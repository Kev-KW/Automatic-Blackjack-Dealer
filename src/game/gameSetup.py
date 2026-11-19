"""Select the player count and launch new blackjack games."""

import time

from src import settings
from src.game import blackjack
from src.gui import screen
from src.hardware.remoteController import (
    RemoteController,
    VirtualRemoteController,
    create_remote_controller,
)


REMOTE_CODES = {
    settings.PLAYER_1_HIT,
    settings.PLAYER_1_STAND,
    settings.PLAYER_2_HIT,
    settings.PLAYER_2_STAND,
    settings.PLAYER_3_HIT,
    settings.PLAYER_3_STAND,
    settings.PLAYER_4_HIT,
    settings.PLAYER_4_STAND,
}
STAND_CODES = {
    settings.PLAYER_1_STAND,
    settings.PLAYER_2_STAND,
    settings.PLAYER_3_STAND,
    settings.PLAYER_4_STAND,
}
HIT_CODES = REMOTE_CODES - STAND_CODES


def read_press(remote: RemoteController) -> tuple[int, str]:
    while True:
        press = remote.wait_for_press()
        if press is not None:
            return press


def select_player_count(remote: RemoteController) -> int:
    player_count = 1
    screen.show_setup(player_count)
    print(f"SELECT NUMBER PLAYERS {player_count}")
    print("Virtual: press A to cycle 1-4 players; press B to confirm.")

    while True:
        _, action = read_press(remote)
        if action == "stand":
            return player_count
        if action == "hit":
            player_count = player_count % 4 + 1
            screen.show_setup(player_count)
            print(f"SELECT NUMBER PLAYERS {player_count}")


def wait_for_new_game(remote: RemoteController) -> bool:
    """Return whether to restart with the same player count."""
    print("PLEASE REMOVE ALL CARDS")
    print("PRESS HIT TO START NEW GAME OR STAND FOR GAME SETUP")
    while True:
        _, action = read_press(remote)
        if action == "hit":
            return True
        if action == "stand":
            return False


def main() -> None:
    remote = create_remote_controller()
    remote.start()
    try:
        while True:
            player_count = select_player_count(remote)
            while True:
                screen.show_game()
                blackjack.game(player_count, remote)
                if not wait_for_new_game(remote):
                    break
                time.sleep(1)
    finally:
        remote.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGame setup stopped.")
