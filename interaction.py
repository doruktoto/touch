import time
import board
import busio
import adafruit_mpr121
import pygame

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Setup pygame mixer for audio playback
pygame.mixer.init()

# Audio file paths
UNPROCESSED_WAV = 'unprocessed.wav'
PROCESSED_WAV = 'processed.wav'

# Debounce time in seconds
DEBOUNCE_TIME = 0.1

# Track last state
last_pressed = None  # None, 0, or 1
current_channel = None

# Preload sounds
unprocessed_sound = pygame.mixer.Sound(UNPROCESSED_WAV)
processed_sound = pygame.mixer.Sound(PROCESSED_WAV)

try:
    while True:
        pin0 = mpr121[0].value
        pin1 = mpr121[1].value
        pressed = None
        if pin1:
            pressed = 1
        elif pin0:
            pressed = 0
        # Priority: pin 1 > pin 0

        if pressed != last_pressed:
            # Stop any currently playing sound
            if current_channel is not None:
                current_channel.stop()
                current_channel = None
            if pressed == 0:
                current_channel = unprocessed_sound.play(-1)  # Loop until stopped
            elif pressed == 1:
                current_channel = processed_sound.play(-1)
            last_pressed = pressed
        time.sleep(DEBOUNCE_TIME)
except KeyboardInterrupt:
    pass
finally:
    pygame.mixer.quit()
