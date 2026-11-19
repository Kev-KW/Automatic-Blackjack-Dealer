"""Play a placeholder blackjack game using Raspberry Pi remotes.
 TODO: 
    1. RASPPI CAM
    2. AC Motor Movement based on player count
    3. DC Motor Card Dispense
    4. LCD screen display

"""

import random
import re
import sys
import time

from src import settings
from src.hardware.motorController import MotorController
from src.hardware.remoteController import RemoteController


def terminal_log(message: str) -> None:
    print(message, file=sys.__stdout__, flush=True)


ACTION_MAPPINGS = settings.ACTION_MAPPINGS
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


def player_number_for_position(position: int) -> int:
    """Map physical positions 1, 2, 4, and 5 to remote/player numbers."""
    return {1: 1, 2: 2, 4: 3, 5: 4}[position]


def next_active_position(
    players: list["Player"],
    physical_positions: list[int],
    current_index: int,
) -> int | None:
    """Return the next eligible player's table position, or None for dealer."""
    for next_index in range(current_index + 1, len(players)):
        if players[next_index].is_eligible():
            return physical_positions[next_index]
    return None


def add_card(player: Player) -> int:
    card = get_card()
    player.add_card(card)
    return card


def parse_remote_code(line: str) -> int | None:
    """Extract a decimal remote code from a text line."""
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
        if dealer.cards:
            covered_cards = display_card_value(dealer.cards[0])
            if len(dealer.cards) > 1:
                covered_cards += " [COVERED]"
        else:
            covered_cards = ""
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
    remote: RemoteController,
    players: list[Player],
    dealer: Player,
    dealer_visible_total: int,
    player_number: int,
) -> str:
    """Wait for a valid action from the specified player's remote."""
    while True:
        action_player, action_name = remote.wait_for_press()
        if action_name == "select":
            continue
        if action_player != player_number:
            display_table(
                players,
                dealer,
                dealer_visible_total,
                current_player=player_number,
            )
            print(f"Ignoring action from Player {action_player}.")
            continue
        return action_name


def play_player(
    remote: RemoteController,
    players: list[Player],
    dealer: Player,
    player: Player,
    player_number: int,
    dealer_visible_total: int,
) -> None:
    while player.is_eligible():
        action = read_action(
            remote,
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
            print(f"Player {index} BUSTED!")
        elif dealer.busted:
            print(f"Player {index} WON!")
        elif player.hand > dealer.hand:
            print(f"Player {index} WON!")
        elif player.hand < dealer.hand:
            print(f"Player {index} LOST!")
        else:
            print(f"Player {index} TIED!")


def game(
    player_count: int,
    remote: RemoteController,
) -> None:
    if not 1 <= player_count <= 4:
        raise ValueError("The number of players must be between 1 and 4.")

    players = [Player() for _ in range(player_count)]
    dealer = Player()
    motors = MotorController()
    motors.start()

    try:
        physical_positions = [1, 2, 4, 5][:player_count]

        terminal_log(
            "Initial deal: one card to each player, then the dealer."
        )
        time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
        for _ in range(2):
            for physical_position, player in zip(
                physical_positions,
                players,
                strict=True,
            ):
                motors.move_to_position(physical_position)
                motors.dispense_card(
                    f"Player {player_number_for_position(physical_position)}"
                )
                card = add_card(player)
                terminal_log(
                    f"Fed Player {player_number_for_position(physical_position)} "
                    f"card {display_card_value(card)}"
                )
                terminal_log(
                    f"Card Detected: {display_card_value(card)} "
                    f"for Player {player_number_for_position(physical_position)}."
                )
                dealer_visible_total = dealer.hand
                display_table(players, dealer, dealer_visible_total)
                time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)

            motors.move_to_position(3)
            motors.dispense_card("Dealer")
            card = add_card(dealer)
            terminal_log(f"Fed Dealer card {display_card_value(card)}")
            terminal_log(f"Card Detected: {display_card_value(card)} for Dealer.")

            dealer_visible_total = dealer.hand
            display_table(players, dealer, dealer_visible_total)
            time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)

        for player in players:
            if len(player.cards) == 2 and player.hand == 21:
                player.mark_blackjack()
                player.turn_finished = True
                terminal_log(
                    f"Skipping Player "
                    f"{players.index(player) + 1}: blackjack."
                )
                time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)

        for index, player in enumerate(players, start=1):
            if not player.is_eligible():
                continue

            physical_position = physical_positions[index - 1]
            dealer_visible_total = dealer.hand
            display_table(
                players,
                dealer,
                dealer_visible_total,
                current_player=index,
            )
            terminal_log(
                f"Player {index}'s turn begins at table position "
                f"{physical_position}."
            )
            time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
            motors.move_to_position(physical_position)
            time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)

            while player.is_eligible():
                action = read_action(
                    remote,
                    players,
                    dealer,
                    dealer_visible_total,
                    index,
                )
                if action == "stand":
                    player.mark_stood()
                    terminal_log(f"Player {index} stands.")
                    time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
                    break

                motors.dispense_card(f"Player {index}")
                card = add_card(player)
                terminal_log(
                    f"Fed Player {index} card {display_card_value(card)}"
                )
                terminal_log(
                    f"Card Detected: {display_card_value(card)} "
                    f"for Player {index}."
                )
                display_table(
                    players,
                    dealer,
                    dealer_visible_total,
                    current_player=index,
                )
                time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
                if player.hand > 21:
                    player.mark_busted()
                elif player.hand == 21:
                    player.mark_blackjack()
            player.turn_finished = True

            next_position = next_active_position(
                players,
                physical_positions,
                index - 1,
            )
            if next_position is not None:
                motors.move_to_position(next_position)
                time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
                terminal_log(
                    f"Next player turn at table position {next_position}."
                )
                time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)

        motors.move_to_position(3)
        terminal_log("Dealer's turn.")
        time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)

        dealer_visible_total = dealer.hand
        display_table(
            players,
            dealer,
            dealer_visible_total,
            dealer_revealed=True,
        )
        while dealer.hand < 17:
            time.sleep(DEALER_DRAW_DELAY_SECONDS)
            motors.dispense_card("Dealer")
            card = add_card(dealer)
            terminal_log(f"Fed Dealer card {display_card_value(card)}")
            terminal_log(f"Card Detected: {display_card_value(card)} for Dealer.")
            display_table(
                players,
                dealer,
                dealer.hand,
                dealer_revealed=True,
            )
            time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
            if dealer.hand > 21:
                dealer.mark_busted()
                break
            if dealer.hand == 21:
                dealer.mark_blackjack()
                break
    finally:
        motors.close()

    report_results(players, dealer)


if __name__ == "__main__":
    try:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        remote = RemoteController()
        remote.start()
        try:
            game(count, remote)
        finally:
            remote.close()
    except KeyboardInterrupt:
        print("\nGame stopped.")
    except (ValueError, RuntimeError) as error:
        print(f"Unable to start game: {error}")
