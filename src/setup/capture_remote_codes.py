"""Capture and print raw 433MHz button codes directly with rpi_rf."""

from src.hardware.remoteController import RemoteController


def main() -> None:
    remote = RemoteController()
    remote.start()
    print("Listening for remote presses. Press Ctrl+C to stop.")
    try:
        while True:
            timestamp = remote.device.rx_code_timestamp
            if timestamp is None or timestamp == remote.last_timestamp:
                continue
            remote.last_timestamp = timestamp
            print(f"Received remote code: {remote.device.rx_code}")
    finally:
        remote.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
