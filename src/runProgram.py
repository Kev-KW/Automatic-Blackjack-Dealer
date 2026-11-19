"""Run the mechanical blackjack pipeline from the graphical setup screen."""

import subprocess
import sys
import argparse
import os


def main() -> None:
    """Start the GUI application without starting card vision."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("auto", "virtual", "hardware"),
        default="virtual" if os.name == "nt" else "auto",
        help="choose hardware RXB6 remotes or terminal remotes",
    )
    args = parser.parse_args()

    environment = os.environ.copy()
    environment["PIPELINE_MODE"] = args.mode
    gui_process = subprocess.Popen(
        [sys.executable, "-m", "src.gui.blackjack_gui"],
        env=environment,
    )

    try:
        gui_process.wait()
    except KeyboardInterrupt:
        gui_process.terminate()
    finally:
        gui_process.wait()


if __name__ == "__main__":
    main()
