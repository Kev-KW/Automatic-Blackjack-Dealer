"""Translate received 433MHz button codes into blackjack player actions."""

from src import settings
from src.hardware.remoteController import RemoteController


ACTION_MAPPINGS = [
    (settings.PLAYER_1_HIT, "PLAYER 1 WANTS TO HIT"),
    (settings.PLAYER_1_STAND, "PLAYER 1 WANTS TO STAND"),
    (settings.PLAYER_2_HIT, "PLAYER 2 WANTS TO HIT"),
    (settings.PLAYER_2_STAND, "PLAYER 2 WANTS TO STAND"),
    (settings.PLAYER_3_HIT, "PLAYER 3 WANTS TO HIT"),
    (settings.PLAYER_3_STAND, "PLAYER 3 WANTS TO STAND"),
    (settings.PLAYER_4_HIT, "PLAYER 4 WANTS TO HIT"),
    (settings.PLAYER_4_STAND, "PLAYER 4 WANTS TO STAND"),
]


def main() -> None:
    remote = RemoteController()
    remote.start()
    print("Listening for mapped player actions. Press Ctrl+C to stop.")
    try:
        while True:
            press = remote.read_press()
            if press is None:
                continue
            player, action = press
            print(f"PLAYER {player} WANTS TO {action.upper()}")
    finally:
        remote.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
