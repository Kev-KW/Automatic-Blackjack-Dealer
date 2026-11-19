"""Raspberry Pi GPIO and remote-code mappings for the blackjack dealer."""

PLAYER_1_HIT = 12071169
PLAYER_1_STAND = 12071170
PLAYER_2_HIT = 3179777
PLAYER_2_STAND = 3179778
PLAYER_3_HIT = 3022721
PLAYER_3_STAND = 3022722
PLAYER_4_HIT = 11831921
PLAYER_4_STAND = 11831922

RX_PIN = 17
CONFIRM_REPEATS = 2
RELEASE_GAP = 0.4

# Delay between terminal AC/DC/card-action prints.
TERMINAL_ACTION_DELAY_SECONDS = 2.0

ACTION_MAPPINGS = {
    PLAYER_1_HIT: (1, "hit"),
    PLAYER_1_STAND: (1, "stand"),
    PLAYER_2_HIT: (2, "hit"),
    PLAYER_2_STAND: (2, "stand"),
    PLAYER_3_HIT: (3, "hit"),
    PLAYER_3_STAND: (3, "stand"),
    PLAYER_4_HIT: (4, "hit"),
    PLAYER_4_STAND: (4, "stand"),
}
