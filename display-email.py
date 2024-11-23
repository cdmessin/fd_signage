#!/usr/bin/env python
import signal
import time
import sys
import traceback
import datetime
import os
import imaplib
import socket
import threading
import queue

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from imap_tools import MailBox, MailMessage, A, AND, OR, NOT, MailMessageFlags, MailboxLoginError, MailboxLogoutError
from bs4 import BeautifulSoup
from datetime import timezone

PROCESSED_EMAILS_FILE = '/home/pi/Documents/fd_signage/processed_emails.txt'

#Load Email Settings from .env file
from dotenv import load_dotenv
load_dotenv()
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_HOST = os.environ.get('EMAIL_HOST')

# Configuration for the message
DISPLAY_TIME_MINS = 3
CAD_EMAIL_ADDRESS = "CAD@CABARRUSCOUNTY.US"
SUBJECT_PREFIX = "Dispatch Report"
START_TIME_DATE = datetime.datetime.now().date()
START_TIME = datetime.datetime.now()

# Configuration for the matrix
options = RGBMatrixOptions()
options.drop_privileges=False # Required to read/write the processed emails file
options.rows = 16
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options = options)

# Shared message queue and display control
message_queue = queue.Queue()
display_stop_event = threading.Event()

def display_message(message_text, minutes):
    try:
        print("Displaying Message: ", message_text)
        offscreen_canvas = matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("./fonts/myfont-16px.bdf")
        textColor = graphics.Color(255, 0, 0)
        pos = offscreen_canvas.width

        # Flash Red first
        for i in range(6):
            offscreen_canvas.Fill(255, 0, 0)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(.15)
            offscreen_canvas.Clear()
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(.15)

        # Set loop to show message for given time or until interrupted
        message_end_time = time.time() + 60 * minutes
        display_stop_event.clear()
        while time.time() < message_end_time and not display_stop_event.is_set():
            offscreen_canvas.Clear()
            len = graphics.DrawText(offscreen_canvas, font, pos, font.height, textColor, message_text)
            pos -= 1
            if (pos + len < 0):
                pos = offscreen_canvas.width

            time.sleep(0.02)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

            # Check if a new message is available
            if not message_queue.empty():
                break

        # After timer is up, or if we were interrupted with a new email, clear the screen
        offscreen_canvas.Clear()
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    except KeyboardInterrupt:
        sys.exit(0)

def handle_email(msg, mailbox):
    print('New Message Found:', msg.subject, msg.date)
    # Only process it if this is a valid incident report email. This should be the case already, but we are double checking
    if is_valid_email(msg):
        print("Message is valid incident")

        # Parse the required fields out and add to message queue
        final_message = parse_email(msg)

        # Stop current display if running
        display_stop_event.set()
        # Clear any existing messages in the queue
        while not message_queue.empty():
            message_queue.get()
        # Add new message to queue
        message_queue.put((final_message, DISPLAY_TIME_MINS))
    else:
        print("Message is NOT valid incident, passing")

def is_valid_email(msg):
    correct_subject = msg.subject.startswith(SUBJECT_PREFIX)

    # Ensure both datetimes are timezone-aware
    if msg.date.tzinfo is None:
        # If msg.date is timezone-naive, make START_TIME timezone-naive
        after_startup = msg.date > START_TIME.replace(tzinfo=None)
    else:
        # Make START_TIME timezone-aware
        after_startup = msg.date > START_TIME.replace(tzinfo=msg.date.tzinfo)

    return correct_subject and after_startup

def parse_email(msg):
    """ Parse the email. We expect there to always be 3 bold elements.
        
        The first bold element is "Communications"
        The second bold element is the Nature
        The third bold element is the Address

        return: str: The message we want to display in the format: "Nature - Address"
    """
    parsed_html = BeautifulSoup(msg.html, features="lxml")
    bold_elements = parsed_html.body.find_all('b')
    combined_message = bold_elements[1].text + " - " + bold_elements[2].text
    return combined_message

def get_processed_emails():
    """
    Retrieve a set of processed emails from a file.
    Each line in the file is expected to contain one email uid.
    Returns:
        set: A set of processed email addresses.
    """
    try:
        if not os.path.exists(PROCESSED_EMAILS_FILE):
            open(PROCESSED_EMAILS_FILE, 'w').close()  # Create the file if it does not exist
        with open(PROCESSED_EMAILS_FILE, 'r') as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

def save_processed_email(uid):
    """
    Appends the given email UID to the processed emails file.
    Args:
        uid (str): The unique identifier of the email to be saved.
    """
    with open(PROCESSED_EMAILS_FILE, 'a') as file:
        file.write(f"{uid}\n")

def display_thread():
    """
    Continuously display messages from the queue
    """
    while True:
        try:
            # Reset the stop event
            display_stop_event.clear()
            
            # Wait for a message
            message, minutes = message_queue.get()
            
            # Display the message
            display_message(message, minutes)
        except Exception as e:
            print(f"Display thread error: {e}")
            traceback.print_exc()
            time.sleep(1)

def email_monitor_thread():
    """
    Monitor emails using IMAP IDLE
    """
    done = False
    while not done:
        connection_start_time = time.monotonic()
        connection_live_time = 0.0
        try:
            with MailBox(EMAIL_HOST).login(EMAIL_ADDRESS, EMAIL_PASSWORD) as mailbox:
                # We create a new connection every 30 minutes, this hopefully reduces timeouts and other connection errors
                print('@@ new connection', time.asctime())
                while connection_live_time < 30 * 60:
                    try:
                        # We poll the mailbox using the IDLE method for a minute. If any emails were received during this time, it will return the response
                        responses = mailbox.idle.wait(timeout=60)
                        if responses:
                            print(time.asctime(), 'IDLE responses:', responses) # I'm not sure what this looks like right now.
                            processed_emails = get_processed_emails()
                            retrieved_messages = mailbox.fetch(A(seen=False, from_=CAD_EMAIL_ADDRESS, subject=SUBJECT_PREFIX, date_gte=START_TIME_DATE), mark_seen=False)
                            for msg in retrieved_messages:
                                # Check if we've already processed the email, if not, process it
                                if msg.uid not in processed_emails:
                                    save_processed_email(msg.uid)
                                    handle_email(msg, mailbox)
                    except KeyboardInterrupt:
                        print('~KeyboardInterrupt')
                        done = True
                        break
                    connection_live_time = time.monotonic() - connection_start_time
        except (TimeoutError, ConnectionError,
                imaplib.IMAP4.abort, MailboxLoginError, MailboxLogoutError,
                socket.herror, socket.gaierror, socket.timeout) as e:
            print(f'## Error\n{e}\n{traceback.format_exc()}\nreconnect in a few seconds...')
            time.sleep(5)

def run_program():
    # Check all environment variables have been set first
    if EMAIL_ADDRESS is None or EMAIL_HOST is None or EMAIL_PASSWORD is None:
        print("Unable to load environment variables")
        display_message("System Configuration Error", .3)
        sys.exit(0)

    try:
        # Create display thread
        display_thread_instance = threading.Thread(target=display_thread)
        display_thread_instance.daemon = True
        display_thread_instance.start()

        # Create email monitoring thread
        email_thread = threading.Thread(target=email_monitor_thread)
        email_thread.daemon = True
        email_thread.start()

        # Keep main thread running and handle keyboard interrupt
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nQuitting...")
        sys.exit(0)
    except Exception as e:
        print(f"Main thread error: {e}")
        traceback.print_exc()
        display_message("System Error", .3)
        sys.exit(1)

def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)

    print("\nQuitting...")
    sys.exit(1)

if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    run_program()
