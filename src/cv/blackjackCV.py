"""Play blackjack using camera-recognized cards and Raspberry Pi remotes."""

import sys
import time

from src.game import blackjack
from src.cv.visionModel import VisionCardReader
from src.hardware.remoteController import RemoteController


DEALER_DRAW_DELAY_SECONDS = 3
PLAYER_ACTION_DELAY_SECONDS = 3


def add_card(reader: VisionCardReader, player: blackjack.Player) -> int:
    """Read one card from vision and store ace as its flexible value."""
    rank, values = reader.read_card()
    value = values[0]
    player.add_card(value)
    print(f"Recognized card: {rank}")
    return value


def play_player(
    reader: VisionCardReader,
    remote: RemoteController,
    players: list[blackjack.Player],
    dealer: blackjack.Player,
    player: blackjack.Player,
    player_number: int,
    dealer_visible_total: int,
) -> None:
    while player.is_eligible():
        action = blackjack.read_action(
            remote,
            players,
            dealer,
            dealer_visible_total,
            player_number,
        )
        if action == "stand":
            player.mark_stood()
            break

        add_card(reader, player)
        blackjack.display_table(
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
    reader: VisionCardReader,
    players: list[blackjack.Player],
    dealer: blackjack.Player,
) -> None:
    blackjack.display_table(players, dealer, dealer.hand, dealer_revealed=True)
    while dealer.hand < 17:
        time.sleep(DEALER_DRAW_DELAY_SECONDS)
        add_card(reader, dealer)
        blackjack.display_table(players, dealer, dealer.hand, dealer_revealed=True)
        if dealer.hand > 21:
            dealer.mark_busted()
            break
        if dealer.hand == 21:
            dealer.mark_blackjack()
            break


def game(
    player_count: int,
    remote: RemoteController,
    camera_number: int = 0,
) -> None:
    if not 1 <= player_count <= 4:
        raise ValueError("The number of players must be between 1 and 4.")

    players = [blackjack.Player() for _ in range(player_count)]
    dealer = blackjack.Player()
    with VisionCardReader(camera_number) as reader:
        dealer_visible_total = add_card(reader, dealer)
        add_card(reader, dealer)
        for _ in range(2):
            for player in players:
                add_card(reader, player)

        for player in players:
            if len(player.cards) == 2 and player.hand == 21:
                player.mark_blackjack()
                player.turn_finished = True

        for index, player in enumerate(players, start=1):
            current_player = index if player.is_eligible() else None
            blackjack.display_table(
                players,
                dealer,
                dealer_visible_total,
                current_player=current_player,
            )
            play_player(
                reader,
                remote,
                players,
                dealer,
                player,
                index,
                dealer_visible_total,
            )

        print("Dealer's turn.")
        play_dealer(reader, players, dealer)

    blackjack.report_results(players, dealer)


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
