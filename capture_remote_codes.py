"""Capture and print raw 433MHz button codes from Arduino over serial."""

import serial

import settings


def main() -> None:
    print(f"Opening {settings.SERIAL_PORT} at {settings.BAUD_RATE} baud...")
    with serial.Serial(
        settings.SERIAL_PORT,
        settings.BAUD_RATE,
        timeout=settings.SERIAL_TIMEOUT_SECONDS,
    ) as connection:
        connection.reset_input_buffer()
        connection.write(b"START\n")
        print("Listening for remote presses. Press Ctrl+C to stop.")

        while True:
            line = connection.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if line.startswith("CODE:"):
                print(f"Received remote code: {line.split(':', 1)[1]}")
            else:
                print(line)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
