"""L298N DC card feeder and stepper control for the blackjack dealer."""

import os
import sys
import time

from src import settings

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


# PLACEHOLDER L298N WIRING - change these BCM pins before hardware testing.
DC_ENABLE_PIN = 18
DC_IN1_PIN = 23
DC_IN2_PIN = 24

# Raspberry Pi BCM pins used by the existing AC/stepper circuit.
AC_STEP_PIN = 19
AC_DIR_PIN = 13

DC_RUN_SECONDS = 2.0
STEPS_PER_REV = 800
STEP_DELAY_SECONDS = 0.005
CENTER_STEPS = 200


def terminal_log(message: str) -> None:
    print(message, file=sys.__stdout__, flush=True)

# Existing 800-pulse/revolution stepper positions.
POSITION_STEPS = {
    1: 50,
    2: 125,
    3: 200,
    4: 275,
    5: 350,
}


class MotorController:
    def __init__(self, dry_run: bool | None = None) -> None:
        self.available = GPIO is not None
        if dry_run is None:
            requested_mode = os.environ.get("PIPELINE_MODE", "auto").strip().lower()
            self.dry_run = (
                self.available is False
                or os.name == "nt"
                or requested_mode == "virtual"
            )
        else:
            self.dry_run = dry_run
        self.current_position_steps = CENTER_STEPS
        self.initialized = False

    def start(self) -> None:
        if self.dry_run:
            terminal_log(
                "Motor dry-run: hardware commands will be printed, not sent."
            )
            self.initialized = True
            return

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(AC_STEP_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(AC_DIR_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(DC_ENABLE_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(DC_IN1_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(DC_IN2_PIN, GPIO.OUT, initial=GPIO.LOW)

        self.dc_pwm = GPIO.PWM(DC_ENABLE_PIN, 1000)
        self.dc_pwm.start(0)
        self.initialized = True
        terminal_log("Motor controller initialized.")

    def move_to_position(self, position: int) -> None:
        if position not in POSITION_STEPS:
            raise ValueError(f"Unknown table position: {position}")
        target_steps = POSITION_STEPS[position]
        self.move_to_steps(target_steps)

    def move_to_steps(self, target_steps: int) -> None:
        if not self.initialized:
            raise RuntimeError("Motor controller is not started.")

        difference = target_steps - self.current_position_steps
        if difference == 0:
            terminal_log(
                f"AC turns to position {self.position_for_steps(target_steps)} "
                f"(already at {target_steps} steps)."
            )
            return

        terminal_log(
            f"AC motor: move to table position "
            f"{self.position_for_steps(target_steps)} "
            f"({target_steps} steps)."
        )
        time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
        if self.dry_run:
            terminal_log(
                f"Motor dry-run: AC move {target_steps - self.current_position_steps:+d} steps "
                f"to table position {self.position_for_steps(target_steps)}."
            )
        else:
            direction = GPIO.HIGH if difference > 0 else GPIO.LOW
            GPIO.output(AC_DIR_PIN, direction)
            time.sleep(0.01)
            for _ in range(abs(difference)):
                GPIO.output(AC_STEP_PIN, GPIO.HIGH)
                time.sleep(STEP_DELAY_SECONDS)
                GPIO.output(AC_STEP_PIN, GPIO.LOW)
                time.sleep(STEP_DELAY_SECONDS)

        self.current_position_steps = target_steps

    def dispense_card(self, recipient: str) -> None:
        if not self.initialized:
            raise RuntimeError("Motor controller is not started.")

        terminal_log(
            f"DC motor: feed 1 card to {recipient} "
            f"for {DC_RUN_SECONDS:.1f} seconds."
        )
        time.sleep(settings.TERMINAL_ACTION_DELAY_SECONDS)
        if self.dry_run:
            terminal_log(
                f"Motor dry-run: DC feeder on for "
                f"{DC_RUN_SECONDS:.1f}s for {recipient}."
            )
            time.sleep(0.05)
            return

        terminal_log(f"DC feeder running for {recipient}.")
        GPIO.output(DC_IN1_PIN, GPIO.HIGH)
        GPIO.output(DC_IN2_PIN, GPIO.LOW)
        self.dc_pwm.ChangeDutyCycle(100)
        time.sleep(DC_RUN_SECONDS)
        self.dc_pwm.ChangeDutyCycle(0)
        GPIO.output(DC_IN1_PIN, GPIO.LOW)
        GPIO.output(DC_IN2_PIN, GPIO.LOW)

    def position_for_steps(self, steps: int) -> int:
        for position, position_steps in POSITION_STEPS.items():
            if position_steps == steps:
                return position
        return steps

    def close(self) -> None:
        if not self.initialized:
            return
        if self.dry_run:
            self.initialized = False
            return

        try:
            self.dc_pwm.ChangeDutyCycle(0)
            GPIO.output(DC_IN1_PIN, GPIO.LOW)
            GPIO.output(DC_IN2_PIN, GPIO.LOW)
            GPIO.output(AC_STEP_PIN, GPIO.LOW)
        finally:
            GPIO.cleanup()
            self.initialized = False
