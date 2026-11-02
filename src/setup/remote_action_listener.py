"""Translate received 433MHz button codes into blackjack player actions."""

import time

import serial

from src import settings


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
    print(f"Opening {settings.SERIAL_PORT} at {settings.BAUD_RATE} baud...")
    with serial.Serial(
        settings.SERIAL_PORT,
        settings.BAUD_RATE,
        timeout=settings.SERIAL_TIMEOUT_SECONDS,
    ) as connection:
        # Opening a serial connection commonly resets an Arduino. Wait for
        # setup() to finish before reading codes.
        time.sleep(2)
        connection.reset_input_buffer()
        print("Listening for mapped player actions. Press Ctrl+C to stop.")

        while True:
            line = connection.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if not line.isdigit():
                print(f"Ignoring non-numeric code line: {line}")
                continue

            code = int(line)
            matched_actions = [action for mapped_code, action in ACTION_MAPPINGS if mapped_code > 0 and mapped_code == code]
            if matched_actions:
                for action in matched_actions:
                    print(action)
            else:
                print(f"NOT REGISTERED REMOTE: {code}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
