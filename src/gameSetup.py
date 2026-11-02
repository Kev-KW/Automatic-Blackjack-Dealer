"""Select the player count and launch new blackjack games."""

import time

import serial

import blackjack
import screen
import settings


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


def read_code(connection: serial.Serial) -> int | None:
    while True:
        line = connection.readline().decode(errors="ignore").strip()
        if not line:
            continue
        code = blackjack.parse_remote_code(line)
        if code is None:
            continue
        return code


def select_player_count(connection: serial.Serial) -> int:
    player_count = 1
    screen.show_setup(player_count)
    print(f"SELECT NUMBER PLAYERS {player_count}")
    print("Press any remote to increase. Press any STAND to confirm.")

    while True:
        code = read_code(connection)
        if code not in REMOTE_CODES:
            continue
        if code in STAND_CODES:
            return player_count

        player_count = player_count % 4 + 1
        screen.show_setup(player_count)
        print(f"SELECT NUMBER PLAYERS {player_count}")


def wait_for_new_game(connection: serial.Serial) -> bool:
    """Return whether to restart with the same player count."""
    print("PLEASE REMOVE ALL CARDS")
    print("PRESS HIT TO START NEW GAME OR STAND FOR GAME SETUP")
    while True:
        code = read_code(connection)
        if code in HIT_CODES:
            connection.reset_input_buffer()
            return True
        if code in STAND_CODES:
            connection.reset_input_buffer()
            return False


def main() -> None:
    print(f"Opening {settings.SERIAL_PORT} at {settings.BAUD_RATE} baud...")
    with serial.Serial(
        settings.SERIAL_PORT,
        settings.BAUD_RATE,
        timeout=settings.SERIAL_TIMEOUT_SECONDS,
    ) as connection:
        time.sleep(2)
        connection.reset_input_buffer()

        while True:
            player_count = select_player_count(connection)
            connection.reset_input_buffer()
            while True:
                screen.show_game()
                blackjack.game(player_count, connection)
                if not wait_for_new_game(connection):
                    break
                time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGame setup stopped.")
    except serial.SerialException as error:
        print(f"Unable to communicate with Arduino: {error}")
