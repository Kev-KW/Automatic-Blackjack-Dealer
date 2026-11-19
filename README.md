# Automatic-Blackjack-Dealer
This project runs a mechanical blackjack dealer on a Raspberry Pi using an
RXB6 433 MHz receiver, a stepper motor, and an L298N-controlled DC card feeder.
CV is currently separate and is not started by the mechanical pipeline.

## 433 MHz Raspberry Pi remote setup

### 1) Wire the Raspberry Pi components

The current code uses the following Raspberry Pi **BCM** pin numbers:

| Device | Pi GPIO pin | BCM number | Physical pin |
|---|---|---:|---:|
| RXB6 DATA | GPIO 17 | 17 | 11 |
| Stepper driver STEP | GPIO 19 | 19 | 35 |
| Stepper driver DIR | GPIO 13 | 13 | 33 |
| L298N ENA/DC enable | GPIO 18 | 18 | 12 |
| L298N IN1 | GPIO 23 | 23 | 16 |
| L298N IN2 | GPIO 24 | 24 | 18 |

#### RXB6 433 MHz receiver

Connect:

- RXB6 `VCC` -> Raspberry Pi `5V`
- RXB6 `GND` -> Raspberry Pi `GND`
- RXB6 `DATA` -> Raspberry Pi BCM GPIO 17 / physical pin 11

Do not connect the receiver's data pin directly to 5 V logic. The Pi is the
3.3 V logic device.

#### AC/stepper motor driver

The code writes pulses to BCM GPIO 19 and direction to BCM GPIO 13. Connect
those two pins to the stepper driver's `STEP` and `DIR` inputs. Connect the
stepper driver's `GND` to a Raspberry Pi ground, and connect the motor supply
as required by the specific stepper driver.

The driver must be configured for:

- 800 pulses per revolution
- 1/4 microstepping
- The step delay currently set to 0.005 seconds

The table positions in `src/hardware/motorController.py` are:

| Table position | Step value | Approximate angle |
|---|---:|---:|
| Player 1 | 50 | 22.5 degrees |
| Player 2 | 125 | 56.25 degrees |
| Dealer | 200 | 90 degrees |
| Player 4 | 275 | 123.75 degrees |
| Player 5 | 350 | 157.5 degrees |

Before hardware use, physically position the arm at the center/dealer position
and set the code's initial position to 200 steps.

#### L298N DC card feeder

The L298N values in `src/hardware/motorController.py` are placeholders:

- BCM GPIO 18 / physical pin 12 -> `ENA`
- BCM GPIO 23 / physical pin 16 -> `IN1`
- BCM GPIO 24 / physical pin 18 -> `IN2`

The DC feeder motor connects across L298N `OUT1` and `OUT2`.

Also connect:

- L298N `GND` -> common ground with the Raspberry Pi
- L298N `VCC`/motor supply -> the appropriate 12 V motor supply
- L298N `5 V`/logic supply -> Pi 5 V only if the L298N board's configuration
  requires and supports it
- Do not connect the 12 V motor supply to a Raspberry Pi GPIO or 5 V pin

Remove or leave the L298N ENA jumper open as appropriate for your board, so
GPIO 18 can control motor speed. Verify the DC motor direction and swap OUT1
and OUT2 or IN1 and IN2 if the feeder spins backward.

Use a common ground between the Pi, RXB6 receiver, stepper driver, and L298N.
Use separate motor and logic power supplies or a regulated supply arrangement
for the motors. Disconnect motor power while changing wiring.

### 2) Install Python dependencies
```bash
python3 -m pip install rpi-gpio rpi-rf
```
### 3) Capture button codes
Run directly on the Raspberry Pi:
   ```bash
   python3 -m src.setup.capture_remote_codes
   ```
Press each remote button and copy the printed decimal codes into
`src/settings.py`:
   - `PLAYER_1_HIT`, `PLAYER_1_STAND`
   - `PLAYER_2_HIT`, `PLAYER_2_STAND`
   - `PLAYER_3_HIT`, `PLAYER_3_STAND`
   - `PLAYER_4_HIT`, `PLAYER_4_STAND`

### 4) Run action listener
```bash
python3 -m src.setup.remote_action_listener
```

When a mapped button is pressed, it prints messages like:
- `PLAYER 1 WANTS TO HIT`
- `PLAYER 2 WANTS TO STAND`

### 5) Run the blackjack game
Run the mechanical game directly:
```bash
python3 -m src.game.blackjack 4
```

The game waits for each player's configured HIT or STAND remote button. Card
values are currently placeholders generated randomly from 1 through 10.

### 6) Run game setup
To select the number of players and restart games using the remotes:
```bash
python3 -m src.game.gameSetup
```

Press any registered remote button to cycle from 1 through 4 players. Press
any registered STAND button to confirm the player count and start blackjack.
After a game ends, remove all cards and press any button to start setup again.

### 7) Run the graphical display
To show setup and game output in a black window with green text:
```bash
python3 -m src.gui.blackjack_gui
```

### 8) Run the GUI and mechanical pipeline
To start the GUI and mechanical game pipeline without vision:
```bash
python3 -m src.runProgram
```

### 8a) Run virtually on Windows
To run without Raspberry Pi GPIO or remote hardware:
```powershell
py -3 -m src.runProgram --mode virtual
```

Virtual terminal controls:
- During setup, press `A` repeatedly to cycle from 1 to 4 players.
- During setup, press `B` to confirm the player count.
- During play, press `1`, `2`, `3`, or `4` to select the active player.
- Then press `A` for HIT or `B` for STAND.
- Motor and dealt-card events are printed in the terminal.
- Press `Q` or `Escape` to quit.

The vision model is not started by this launcher. Close the GUI to stop the
application.

## Mechanical pipeline without CV

Run the GUI and select the number of players:
```bash
python3 -m src.runProgram
```

The mechanical pipeline uses the Raspberry Pi RXB6 remote setup and the
stepper. It does not start the vision model. The L298N motor values are placeholders in
`src/hardware/motorController.py`:

- L298N DC enable: BCM 18
- L298N IN1: BCM 23
- L298N IN2: BCM 24
- DC card feeder run time: 2 seconds
- AC/stepper STEP: BCM 19
- AC/stepper DIR: BCM 13

Change the placeholder pins and verify them against the hardware before live
operation. On a machine without `RPi.GPIO`, motor commands enter a dry-run
mode and are printed instead of sent to hardware.
