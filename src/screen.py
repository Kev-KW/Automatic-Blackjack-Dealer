"""Thread-safe state bridge between the game logic and the GUI."""

from collections import deque
from threading import Lock


_lock = Lock()
_mode = "game"
_player_count = 1
_output = deque()
_clear_game = False


def show_setup(player_count: int) -> None:
    global _mode, _player_count
    with _lock:
        _mode = "setup"
        _player_count = player_count


def show_game() -> None:
    global _mode, _clear_game
    with _lock:
        _mode = "game"
        _clear_game = True


def add_output(text: str) -> None:
    with _lock:
        _output.append(text)


def drain() -> tuple[str, int, list[str]]:
    global _clear_game
    with _lock:
        output = list(_output)
        _output.clear()
        clear_game = _clear_game
        _clear_game = False
        return _mode, _player_count, output + (["\x00CLEAR_GAME"] if clear_game else [])
