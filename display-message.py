#!/usr/bin/env python
import signal
import time
import sys
import traceback
import datetime

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from imap_tools import MailBox, A, AND, OR, NOT

# Configuration for the message
DISPLAY_TIME_MINS = .5

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 16
options.chain_length = 4
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options = options)

def display_message(message_text, minutes):
    try:
        print("Display Message entered")
        offscreen_canvas = matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("./fonts/myfont-16px.bdf")
        textColor = graphics.Color(255, 0, 0)
        pos = offscreen_canvas.width/2

        # Flash Red first
        for i in range(1):
            offscreen_canvas.Fill(255, 0, 0)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(.15)
            offscreen_canvas.Clear()
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(.15)

        message_end_time = time.time() + 60 * minutes
        while time.time() < message_end_time:
            offscreen_canvas.Clear()
            len = graphics.DrawText(offscreen_canvas, font, pos, font.height, textColor, message_text)
            pos -= 1
            if (pos + len < 0):
                pos = offscreen_canvas.width

            time.sleep(0.015)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    except KeyboardInterrupt:
        sys.exit(0)

def run_program():
    try:
        # Currently set to display a hardcoded version of the message
        display_message("LIFTING ASSISTANCE - 8500 FLOWE FARM RD", DISPLAY_TIME_MINS)
    except Exception as e:
        traceback.print_exc()

def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)

    print("\nQuitting...")
    sys.exit(1)

if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    run_program()
