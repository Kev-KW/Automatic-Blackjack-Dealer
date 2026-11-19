"""Blackjack dealer: camera rank recognition + four RXB6 remotes.

Run with: python3 blackjack_cv_remote.py 4

Requires, alongside this file:
    detectRank.py
    roi.json
    remote_codes.json  (created by the remote calibration program)

Card-feed actuator is NOT defined in the original blackjack1.2.py.  For now,
manual advancement is used; replace dispense_card() with real feed-motor
control once its wiring is known.
"""

import json
import math
import sys
import time
from pathlib import Path

import cv2
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from rpi_rf import RFDevice

from detectRank import detectRank

ROOT = Path(__file__).resolve().parent
ROI_FILE = ROOT / "roi.json"
REMOTE_FILE = ROOT / "remote_codes.json"
CAPTURE_FILE = ROOT / "capture.jpg"

# Raspberry Pi BCM pin numbers (from your tested wiring)
STEP_PIN = 19
DIR_PIN = 13
RX_PIN = 17

STEPS_PER_REV = 800  # 1/4 microstepping on a 200-step motor
STEP_DELAY = 0.005
CLOCKWISE = GPIO.LOW
COUNTERCLOCKWISE = GPIO.HIGH
CENTER_STEPS = 200  # 90 degrees

# Four player positions and dealer at center, all within 22.5-157.5 degrees.
PLAYER_STEPS = [50, 125, 275, 350]
DEALER_STEPS = CENTER_STEPS

# RF codes frequently repeat while a remote button is held.
CONFIRM_REPEATS = 2  # Set to 1 if your remote sends only one decoded message.
RELEASE_GAP = 0.4

# Optional minimum *higher-is-better* similarity accepted by detectRank().
# Leave as None until you know what score values your detector produces.
MIN_SIMILARITY = None

# Expand the calibration ROI around its original center in BOTH dimensions.
# 1.5 makes each dimension 50% larger; 1.0 leaves it unchanged.
ROI_WIDTH_SCALE = 1.2
ROI_HEIGHT_SCALE = 1.2

current_stepper_steps = CENTER_STEPS  # Motor MUST physically start at 90 degrees.


def load_roi():
    with ROI_FILE.open("r") as file:
        data = json.load(file)
    return tuple(int(data[k]) for k in ("x", "y", "w", "h"))


def load_remote_codes(num_players):
    with REMOTE_FILE.open("r") as file:
        data = json.load(file)
    for remote in range(1, num_players + 1):
        for button in (1, 2):
            entry = data.get(str(remote), {}).get(str(button))
            if not entry or "code" not in entry or "protocol" not in entry:
                raise ValueError(
                    f"Remote {remote}, Button {button} is not configured in "
                    f"{REMOTE_FILE.name}"
                )
    return data


def move_to(target_steps):
    """Move between absolute 800-pulse/revolution coordinates."""
    global current_stepper_steps

    difference = target_steps - current_stepper_steps
    if difference == 0:
        return

    GPIO.output(
        DIR_PIN, COUNTERCLOCKWISE if difference > 0 else CLOCKWISE
    )
    time.sleep(0.01)  # Allow the driver to register the new direction.

    for _ in range(abs(difference)):
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(STEP_DELAY)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(STEP_DELAY)

    current_stepper_steps = target_steps
    print(f"Stepper at {target_steps * 360 / STEPS_PER_REV:.2f} degrees")


def normalize_rank(rank):
    if rank is None:
        raise ValueError("detectRank() returned no rank")
    rank = str(rank).strip().upper()
    if rank == "T":
        rank = "10"
    if rank not in {"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}:
        raise ValueError(f"Unrecognized rank: {rank!r}")
    return rank


def detect_card(camera, roi_config):
    """Read the visible top card. On CV failure, wait for reposition + Enter."""
    x, y, w, h = roi_config

    while True:
        try:
            start = time.perf_counter()
            camera.capture_file(str(CAPTURE_FILE))
            image = cv2.imread(str(CAPTURE_FILE))
            if image is None:
                raise ValueError("Camera image could not be opened")

            height, width = image.shape[:2]
            if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
                raise ValueError(
                    f"ROI {(x, y, w, h)} is outside the {width}x{height} image. "
                    "Recalibrate roi.json using this camera configuration."
                )

            # Expand width AND height, centered on the calibration rectangle.
            # Constrain the crop to image bounds, shifting it inward as needed.
            center_x = x + w / 2
            center_y = y + h / 2
            expanded_width = min(width, max(w, round(w * ROI_WIDTH_SCALE)))
            expanded_height = min(height, max(h, round(h * ROI_HEIGHT_SCALE)))

            x1 = max(0, min(width - expanded_width,
                             round(center_x - expanded_width / 2)))
            y1 = max(0, min(height - expanded_height,
                             round(center_y - expanded_height / 2)))
            x2 = x1 + expanded_width
            y2 = y1 + expanded_height

            roi = image[y1:y2, x1:x2]
            print(f"Calibrated ROI: x={x}, y={y}, w={w}, h={h}")
            print(f"Expanded ROI: x={x1}, y={y1}, w={x2 - x1}, h={y2 - y1}")
            rank, score = detectRank(CAPTURE_FILE, roi)
            rank = normalize_rank(rank)

            score_value = float(score)
            if not math.isfinite(score_value):
                raise ValueError(f"Invalid similarity score: {score!r}")
            if MIN_SIMILARITY is not None and score_value < MIN_SIMILARITY:
                raise ValueError(
                    f"Low similarity: {score_value} "
                    f"(minimum {MIN_SIMILARITY})"
                )

            elapsed = time.perf_counter() - start
            print(f"Card detected: {rank} (similarity: {score}, {elapsed:.2f}s)")
            return rank

        except Exception as error:
            print(f"\nCV ERROR: {type(error).__name__}: {error}")
            print(f"Check captured image: {CAPTURE_FILE}")
            input("Reposition the top card, then press Enter to try again...")


def dispense_card(recipient):
    """Temporary MANUAL feeder. Replace this with feed-wheel motor control.

    The camera looks at a preloaded stack, so the currently recognized card
    MUST be removed before the next capture; otherwise it gets counted again.
    """
    input(
        f"Dispense the recognized top card to {recipient} and expose the next "
        "card, then press Enter..."
    )


class RemoteInput:
    def __init__(self, device, codes):
        self.device = device
        self.codes = codes
        self.last_timestamp = device.rx_code_timestamp
        self.last_key = None
        self.last_time = 0.0
        self.repeat_count = 0
        self.reported = False

    def read_press(self):
        """Return (remote_number, button_number) once per RF burst."""
        timestamp = self.device.rx_code_timestamp
        if timestamp is None or timestamp == self.last_timestamp:
            return None
        self.last_timestamp = timestamp

        code = self.device.rx_code
        protocol = self.device.rx_proto
        if not code:
            return None

        key = (int(code), int(protocol))
        now = time.monotonic()
        if key == self.last_key and (now - self.last_time) < RELEASE_GAP:
            self.repeat_count += 1
        else:
            self.repeat_count = 1
            self.reported = False
        self.last_key = key
        self.last_time = now

        if self.repeat_count < CONFIRM_REPEATS or self.reported:
            return None
        self.reported = True

        for remote, buttons in self.codes.items():
            for button, stored in buttons.items():
                if key == (int(stored["code"]), int(stored["protocol"])):
                    return int(remote), int(button)
        print(f"Unrecognized RF signal: code={code}, protocol={protocol}")
        return None

    def wait_for_player(self, player_number):
        print(
            f"Player {player_number}: press Button 1 to HIT or "
            "Button 2 to STAND."
        )
        while True:
            press = self.read_press()
            if press is not None:
                remote, button = press
                if remote == player_number:
                    return "h" if button == 1 else "s"
                print(f"Ignored Remote {remote}, Button {button}; waiting for Remote {player_number}")
            time.sleep(0.01)


class Player:
    def __init__(self, position_steps):
        self.position_steps = position_steps
        self.cards = []
        self.stood = False

    def add_card(self, rank):
        self.cards.append(rank)

    def total(self):
        # All aces initially count as 1, then upgrade to 11 if safe.
        total = sum(
            1 if r == "A" else 10 if r in {"10", "J", "Q", "K"} else int(r)
            for r in self.cards
        )
        for rank in self.cards:
            if rank == "A" and total + 10 <= 21:
                total += 10
        return total

    @property
    def busted(self):
        return self.total() > 21

    @property
    def blackjack(self):
        return len(self.cards) == 2 and self.total() == 21


def deal_to(player, recipient, camera, roi_config):
    move_to(player.position_steps)
    rank = detect_card(camera, roi_config)
    player.add_card(rank)
    print(f"{recipient}: {player.cards} (total {player.total()})")
    dispense_card(recipient)


def game(num_players, camera, roi_config, remotes):
    players = [Player(PLAYER_STEPS[i]) for i in range(num_players)]
    dealer = Player(DEALER_STEPS)

    # Preserve the initial deal order in your original blackjack1.2.py.
    for _ in range(2):
        deal_to(dealer, "Dealer", camera, roi_config)
        for index, player in enumerate(players, start=1):
            deal_to(player, f"Player {index}", camera, roi_config)

    for index, player in enumerate(players, start=1):
        move_to(player.position_steps)
        if player.blackjack:
            print(f"Player {index}: natural blackjack!")
            continue

        while player.total() < 21 and not player.stood:
            command = remotes.wait_for_player(index)
            if command == "s":
                player.stood = True
                print(f"Player {index} stands at {player.total()}")
            else:
                deal_to(player, f"Player {index}", camera, roi_config)

        if player.busted:
            print(f"Player {index} busts ({player.total()})")

    move_to(dealer.position_steps)
    print(f"Dealer: {dealer.cards} (total {dealer.total()})")
    if not all(player.busted for player in players):
        # Dealer stands on all 17s, including soft 17.
        while dealer.total() < 17:
            deal_to(dealer, "Dealer", camera, roi_config)

    print("\n===== RESULTS =====")
    for index, player in enumerate(players, start=1):
        if player.busted:
            outcome = "Dealer wins (player busted)"
        elif dealer.busted:
            outcome = "Player wins (dealer busted)"
        elif player.blackjack and not dealer.blackjack:
            outcome = "Player wins (blackjack)"
        elif dealer.blackjack and not player.blackjack:
            outcome = "Dealer wins (blackjack)"
        elif player.total() > dealer.total():
            outcome = "Player wins"
        elif player.total() < dealer.total():
            outcome = "Dealer wins"
        else:
            outcome = "Tie"
        print(f"Player {index}: {player.total()} vs dealer {dealer.total()} -- {outcome}")


def main():
    num_players = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    if not 1 <= num_players <= 4:
        raise ValueError("Player count must be between 1 and 4")

    roi_config = load_roi()
    remote_codes = load_remote_codes(num_players)

    camera = None
    receiver = None
    camera_started = False
    gpio_ready = False

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(STEP_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(DIR_PIN, GPIO.OUT, initial=GPIO.LOW)
        gpio_ready = True

        receiver = RFDevice(RX_PIN)
        receiver.enable_rx()
        remotes = RemoteInput(receiver, remote_codes)

        camera = Picamera2()
        # Match the still configuration used when roi.json was calibrated.
        camera.configure(camera.create_still_configuration())
        camera.start()
        camera_started = True
        time.sleep(2)  # Once at startup, not between every card.

        print(f"Blackjack starting with {num_players} player(s).")
        print("Ensure the motor is PHYSICALLY centered at 90 degrees.")
        print("Card feeding is currently MANUAL (see dispense_card()).")
        game(num_players, camera, roi_config, remotes)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    finally:
        if gpio_ready:
            print("Returning stepper to 90 degrees...")
            try:
                move_to(CENTER_STEPS)
            except Exception as error:
                print(f"Could not return to center: {error}")
        if camera is not None:
            if camera_started:
                camera.stop()
            camera.close()
        if receiver is not None:
            receiver.cleanup()
        if gpio_ready:
            GPIO.cleanup()


if __name__ == "__main__":
    main()
