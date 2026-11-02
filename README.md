# Automatic-Blackjack-Dealer
This project aims to track blackjack cards through CV model while utilizing Arduino &amp; Bluetooth to allow players to HIT/Stand using 433 MHz Remote controllers. 

## 433 MHz remote setup

### 1) Upload Arduino sketch
Upload `arduino_receiver.ino` to your Arduino.

This sketch sends parseable serial messages like:
- `READY`
- `STREAM:ON`
- `CODE:123456`

### 2) Install Python dependency
```bash
pip install pyserial
```

### 3) Capture button codes
1. Edit `settings.py` and set `SERIAL_PORT`.
2. Run:
   ```bash
   python -m src.setup.capture_remote_codes
   ```
3. Press each remote button and copy the printed decimal codes into:
   - `PLAYER_1_HIT`, `PLAYER_1_STAND`
   - `PLAYER_2_HIT`, `PLAYER_2_STAND`
   - `PLAYER_3_HIT`, `PLAYER_3_STAND`
   - `PLAYER_4_HIT`, `PLAYER_4_STAND`

### 4) Run action listener
```bash
python -m src.setup.remote_action_listener
```

When a mapped button is pressed, it prints messages like:
- `PLAYER 1 WANTS TO HIT`
- `PLAYER 2 WANTS TO STAND`

### 5) Run the blackjack game
Run the game with the number of players as an argument:
```bash
python blackjack.py 4
```

The game waits for each player's configured HIT or STAND remote button. Card
values are currently placeholders generated randomly from 1 through 10.

### 6) Run game setup
To select the number of players and restart games using the remotes:
```bash
python src/gameSetup.py
```

Press any registered remote button to cycle from 1 through 4 players. Press
any registered STAND button to confirm the player count and start blackjack.
After a game ends, remove all cards and press any button to start setup again.

### 7) Run the graphical display
To show setup and game output in a black window with green text:
```bash
python src/blackjack_gui.py
```
