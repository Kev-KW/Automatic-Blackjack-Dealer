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
   python capture_remote_codes.py
   ```
3. Press each remote button and copy the printed decimal codes into:
   - `PLAYER_1_HIT`, `PLAYER_1_STAND`
   - `PLAYER_2_HIT`, `PLAYER_2_STAND`
   - `PLAYER_3_HIT`, `PLAYER_3_STAND`
   - `PLAYER_4_HIT`, `PLAYER_4_STAND`

### 4) Run action listener
```bash
python remote_action_listener.py
```

When a mapped button is pressed, it prints messages like:
- `PLAYER 1 WANTS TO HIT`
- `PLAYER 2 WANTS TO STAND`
