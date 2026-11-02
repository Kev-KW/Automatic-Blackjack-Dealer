"""Play a placeholder blackjack game using the Arduino remote controls."""

import random
import re
import sys
import time

import serial

import settings


ACTION_MAPPINGS = {
    settings.PLAYER_1_HIT: (1, "hit"),
    settings.PLAYER_1_STAND: (1, "stand"),
    settings.PLAYER_2_HIT: (2, "hit"),
    settings.PLAYER_2_STAND: (2, "stand"),
    settings.PLAYER_3_HIT: (3, "hit"),
    settings.PLAYER_3_STAND: (3, "stand"),
    settings.PLAYER_4_HIT: (4, "hit"),
    settings.PLAYER_4_STAND: (4, "stand"),
}
DEALER_DRAW_DELAY_SECONDS = 3
PLAYER_ACTION_DELAY_SECONDS = 3


class Player:
    def __init__(self) -> None:
        self.cards: list[int] = []
        self.busted = False
        self.has_blackjack = False
        self.stood = False
        self.turn_finished = False

    def add_card(self, value: int) -> None:
        self.cards.append(value)

    @property
    def hand(self) -> int:
        total = sum(self.cards)
        if 1 in self.cards and total + 10 <= 21:
            return total + 10
        return total

    def alternate_hand(self) -> int | None:
        total = sum(self.cards)
        if 1 in self.cards and total + 10 <= 21:
            return total
        return None

    def display_hand(self) -> str:
        alternate = self.alternate_hand()
        if alternate is not None:
            return f"{self.hand} ({alternate})"
        return str(self.hand)

    def display_cards(self) -> str:
        return " ".join(display_card_value(card) for card in self.cards)

    def is_eligible(self) -> bool:
        return not self.busted and not self.has_blackjack

    def mark_busted(self) -> None:
        self.busted = True

    def mark_blackjack(self) -> None:
        self.has_blackjack = True

    def mark_stood(self) -> None:
        self.stood = True


def get_card() -> int:
    """Return a placeholder card value until card tracking is integrated."""
    return random.randint(1, 10)


def display_card_value(value: int) -> str:
    return "A" if value == 1 else str(value)


def add_card(player: Player) -> int:
    card = get_card()
    player.add_card(card)
    return card


def parse_remote_code(line: str) -> int | None:
    """Extract a decimal remote code from supported Arduino output formats."""
    line = line.strip()
    if line.isdigit():
        return int(line)

    match = re.fullmatch(r"(?:CODE:|Decimal Code:\s*)(\d+)", line)
    if match is not None:
        return int(match.group(1))
    return None


def display_table(
    players: list[Player],
    dealer: Player,
    visible_dealer_total: int,
    current_player: int | None = None,
    dealer_revealed: bool = False,
) -> None:
    print()
    if dealer_revealed:
        dealer_label = f"DEALER: {dealer.display_hand()}"
        dealer_cards = dealer.display_cards()
    else:
        covered_cards = display_card_value(dealer.cards[0])
        if len(dealer.cards) > 1:
            covered_cards += " [COVERED]"
        dealer_label = f"DEALER: {display_card_value(visible_dealer_total)}"
        dealer_cards = covered_cards
    print(f"{dealer_label:<20}|| {dealer_cards}")

    for index, player in enumerate(players, start=1):
        if player.busted:
            marker = " <--- BUST"
        elif player.has_blackjack:
            marker = " <--- BLACKJACK"
        elif player.stood:
            marker = " <--- STAND"
        elif index == current_player:
            marker = " <--- CURRENT TURN"
        elif player.turn_finished:
            marker = " <---"
        else:
            marker = ""
        player_label = f"PLAYER {index}: {player.display_hand()}"
        print(f"{player_label:<20}|| {player.display_cards()}{marker}")
    print()


def read_action(
    connection: serial.Serial,
    players: list[Player],
    dealer: Player,
    dealer_visible_total: int,
    player_number: int,
) -> str:
    """Wait for a valid action from the specified player's remote."""
    while True:
        line = connection.readline().decode(errors="ignore").strip()
        if not line:
            continue
        code = parse_remote_code(line)
        if code is None:
            print(f"Ignoring non-numeric code line: {line}")
            continue

        action = ACTION_MAPPINGS.get(code)
        if action is None:
            print(f"NOT REGISTERED REMOTE: {code}")
            continue
        action_player, action_name = action
        if action_player != player_number:
            print(f"Ignoring action from Player {action_player}.")
            display_table(
                players,
                dealer,
                dealer_visible_total,
                current_player=player_number,
            )
            continue
        return action_name


def play_player(
    connection: serial.Serial,
    players: list[Player],
    dealer: Player,
    player: Player,
    player_number: int,
    dealer_visible_total: int,
) -> None:
    while player.is_eligible():
        action = read_action(
            connection,
            players,
            dealer,
            dealer_visible_total,
            player_number,
        )
        if action == "stand":
            player.mark_stood()
            break

        add_card(player)
        display_table(
            players,
            dealer,
            dealer_visible_total,
            current_player=player_number,
        )
        if player.hand > 21:
            player.mark_busted()
        elif player.hand == 21:
            player.mark_blackjack()
        else:
            time.sleep(PLAYER_ACTION_DELAY_SECONDS)
            connection.reset_input_buffer()
    player.turn_finished = True


def play_dealer(
    players: list[Player],
    dealer: Player,
) -> None:
    display_table(players, dealer, dealer.hand, dealer_revealed=True)
    while dealer.hand < 17:
        time.sleep(DEALER_DRAW_DELAY_SECONDS)
        add_card(dealer)
        display_table(players, dealer, dealer.hand, dealer_revealed=True)
        if dealer.hand > 21:
            dealer.mark_busted()
            break
        if dealer.hand == 21:
            dealer.mark_blackjack()
            break


def report_results(players: list[Player], dealer: Player) -> None:
    for index, player in enumerate(players, start=1):
        if player.busted:
            print(f"Player {index} busted.")
        elif dealer.busted:
            print(f"Dealer busted. Player {index} wins.")
        elif player.hand > dealer.hand:
            print(f"Player {index} wins with hand: {player.hand}")
        elif player.hand < dealer.hand:
            print(f"Dealer wins against Player {index} with hand: {dealer.hand}")
        else:
            print(f"Player {index} and Dealer tie with hand: {player.hand}")


def game(player_count: int) -> None:
    if not 1 <= player_count <= 4:
        raise ValueError("The number of players must be between 1 and 4.")

    players = [Player() for _ in range(player_count)]
    dealer = Player()

    with serial.Serial(
        settings.SERIAL_PORT,
        settings.BAUD_RATE,
        timeout=settings.SERIAL_TIMEOUT_SECONDS,
    ) as connection:
        time.sleep(2)
        connection.reset_input_buffer()
        print(f"Connected to Arduino on {settings.SERIAL_PORT}.")

        dealer_visible_total = add_card(dealer)
        add_card(dealer)
        for _ in range(2):
            for player in players:
                add_card(player)

        for player in players:
            if len(player.cards) == 2 and player.hand == 21:
                player.mark_blackjack()
                player.turn_finished = True

        for index, player in enumerate(players, start=1):
            current_player = index if player.is_eligible() else None
            display_table(
                players,
                dealer,
                dealer_visible_total,
                current_player=current_player,
            )
            play_player(
                connection,
                players,
                dealer,
                player,
                index,
                dealer_visible_total,
            )
        print("Dealer's turn.")
        play_dealer(players, dealer)

    report_results(players, dealer)


if __name__ == "__main__":
    try:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        game(count)
    except KeyboardInterrupt:
        print("\nGame stopped.")
    except (ValueError, serial.SerialException) as error:
        print(f"Unable to start game: {error}")
