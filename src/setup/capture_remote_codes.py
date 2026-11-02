"""Capture and print raw 433MHz button codes from Arduino over serial."""

import time

import serial

from src import settings


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
        print("Listening for remote presses. Press Ctrl+C to stop.")

        while True:
            line = connection.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if line.isdigit():
                print(f"Received remote code: {line}")
            else:
                print(line)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
