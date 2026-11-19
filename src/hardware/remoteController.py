"""RXB6 remote-input controller for the Raspberry Pi."""

import time
import os
import queue

try:
    from rpi_rf import RFDevice
except ImportError:
    RFDevice = None

from src import settings


class RemoteController:
    def __init__(self) -> None:
        if RFDevice is None:
            raise RuntimeError(
                "rpi_rf is not installed. Install it with: "
                "python3 -m pip install rpi-rf"
            )
        self.device = RFDevice(settings.RX_PIN)
        self.last_timestamp = None
        self.last_key = None
        self.last_time = 0.0
        self.repeat_count = 0

    def start(self) -> None:
        self.device.enable_rx()
        self.last_timestamp = self.device.rx_code_timestamp

    def read_press(self) -> tuple[int, str] | None:
        timestamp = self.device.rx_code_timestamp
        if timestamp is None or timestamp == self.last_timestamp:
            time.sleep(0.01)
            return None
        self.last_timestamp = timestamp

        code = self.device.rx_code
        if not code:
            return None

        key = int(code)
        now = time.monotonic()
        if key == self.last_key and now - self.last_time < settings.RELEASE_GAP:
            self.repeat_count += 1
        else:
            self.repeat_count = 1
        self.last_key = key
        self.last_time = now

        if self.repeat_count < settings.CONFIRM_REPEATS:
            return None

        for action_code, (remote, action) in settings.ACTION_MAPPINGS.items():
            if key == action_code:
                return remote, action
        print(f"Unrecognized RF code: {key}")
        return None

    def wait_for_press(self) -> tuple[int, str]:
        while True:
            press = self.read_press()
            if press is not None:
                return press

    def close(self) -> None:
        self.device.cleanup()


class VirtualRemoteController:
    """Terminal remote simulation for Windows and hardware-free testing."""

    def __init__(self) -> None:
        self.selected_player = 1
        self._keys = queue.Queue()

    def start(self) -> None:
        print(
            "Virtual remotes enabled: during setup press A to cycle player count "
            "and B to confirm; during play press 1-4 to select a player."
        )

    def submit_key(self, key: str) -> None:
        self._keys.put(key.strip().upper())

    def read_press(self) -> tuple[int, str] | None:
        try:
            entry = self._keys.get_nowait()
        except queue.Empty:
            time.sleep(0.01)
            return None

        if entry in {"1", "2", "3", "4"}:
            self.selected_player = int(entry)
            print(f"Virtual remote player selected: {self.selected_player}")
            return self.selected_player, "select"
        if entry == "A":
            print(
                f"Virtual Remote {self.selected_player}: HIT "
                f"(Player {self.selected_player})"
            )
            return self.selected_player, "hit"
        if entry == "B":
            print(
                f"Virtual Remote {self.selected_player}: STAND "
                f"(Player {self.selected_player})"
            )
            return self.selected_player, "stand"

        print("Virtual remote ignores input; use 1-4, A, or B.")
        return None

    def wait_for_press(self) -> tuple[int, str]:
        while True:
            press = self.read_press()
            if press is not None:
                return press

    def close(self) -> None:
        pass


_virtual_controller: VirtualRemoteController | None = None


def submit_virtual_key(key: str) -> None:
    global _virtual_controller
    if _virtual_controller is not None:
        _virtual_controller.submit_key(key)


def create_remote_controller(mode: str | None = None) -> RemoteController | VirtualRemoteController:
    global _virtual_controller
    mode = (mode or os.environ.get("PIPELINE_MODE", "auto")).strip().lower()
    if mode == "virtual":
        _virtual_controller = VirtualRemoteController()
        return _virtual_controller
    if mode == "hardware":
        try:
            return RemoteController()
        except RuntimeError as error:
            print(f"{error}")
            print("Hardware RF unavailable; using virtual remotes.")
            return VirtualRemoteController()
    if os.name == "nt" or RFDevice is None:
        print("Raspberry Pi RF library unavailable; using virtual remotes.")
        return VirtualRemoteController()
    try:
        return RemoteController()
    except RuntimeError as error:
        print(f"{error}")
        print("Hardware RF unavailable; using virtual remotes.")
        return VirtualRemoteController()
