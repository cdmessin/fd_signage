#!/usr/bin/env python
import signal
import time
import sys
import traceback
import datetime
import os

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from imap_tools import MailBox, MailMessage, A, AND, OR, NOT, MailMessageFlags
from bs4 import BeautifulSoup

PROCESSED_EMAILS_FILE = '/home/pi/Documents/fd_signage/processed_emails.txt'

#Load Email Settings from .env file
from dotenv import load_dotenv
load_dotenv()
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_HOST = os.environ.get('EMAIL_HOST')

# Configuration for the message
DISPLAY_TIME_MINS = .2
CAD_EMAIL_ADDRESS = "CAD@CABARRUSCOUNTY.US"
SUBJECT_PREFIX = "Dispatch Report"

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 16
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options = options)

def display_message(message_text, minutes):
    try:
        print("Displaying Message...",)
        offscreen_canvas = matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("./fonts/9x15B.bdf")
        textColor = graphics.Color(255, 255, 255)
        pos = offscreen_canvas.width

        # Flash Red first
        for i in range(6):
            offscreen_canvas.Fill(255, 0, 0)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(.15)
            offscreen_canvas.Clear()
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(.15)

        # Set loop to show message for given time
        message_end_time = time.time() + 60 * minutes
        while time.time() < message_end_time:
            offscreen_canvas.Clear()
            len = graphics.DrawText(offscreen_canvas, font, pos, font.height, textColor, message_text)
            pos -= 1
            if (pos + len < 0):
                pos = offscreen_canvas.width

            time.sleep(0.05)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

        # After timer is up, clear the screen
        offscreen_canvas.Clear()
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    except KeyboardInterrupt:
        sys.exit(0)

def handle_email(msg, mailbox):
    print('New Message Found:', msg.subject, msg.date)
    # Only process it if this is a valid incident report email. This should be the case already, but we are double checking
    if is_valid_email(msg):
        print("Message is valid incident")
        # If desired, we can choose to mark the email as read by uncommenting the following line
        # mailbox.flag(msg.uid, MailMessageFlags.SEEN, True)

        # Pull out the attachment (which is another email)
        # and then parse the required fields out and display it on the sign
        att = msg.attachments[0]
        if '.eml' in att.filename:
            final_message = parse_email_attachment(att)
            display_message(final_message, DISPLAY_TIME_MINS)
        else:
            print('Alert Received: No Email Attachment Found')
            display_message('Alert Received: No Email Attachment Found', DISPLAY_TIME_MINS)

def is_valid_email(msg):
    correct_subject = msg.subject.startswith(SUBJECT_PREFIX)
    attachement_available = len(msg.attachments) >= 1

    return correct_subject and attachement_available

def parse_email_attachment(attachment):
    """ Parse the attached email. We expect there to always be 3 bold elements.
        
        The first bold element is "Communications"
        The second bold element is the Nature
        The third bold element is the Address

        return: str: The message we want to display in the format: "Nature - Address"
    """
    attached_email = MailMessage.from_bytes(attachment.payload)
    parsed_html = BeautifulSoup(attached_email.html, features="lxml")
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
    print("Getting processed emails")
    try:
        if not os.path.exists(PROCESSED_EMAILS_FILE):
            print("Creating file")
            open(PROCESSED_EMAILS_FILE, 'w').close()  # Create the file if it does not exist
        print("File should exist, opening now")
        with open(PROCESSED_EMAILS_FILE, 'r') as file:
            print("Reading file now")
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

def run_program():
    # We only want to get emails after the time that this service was started.
    start_time = datetime.datetime.now().date()
    # Check all environment variables have been set first
    if EMAIL_ADDRESS is None or EMAIL_HOST is None or EMAIL_PASSWORD is None:
        print("Unable to load environment variables")
        display_message("Unable to load environment variables", .3)
        sys.exit(0)
    # Start the main loop
    try:
        with MailBox(EMAIL_HOST).login(EMAIL_ADDRESS, EMAIL_PASSWORD) as mailbox:
            while True:
                print("Checking for email")
                time.sleep(5)
                processed_emails = get_processed_emails()
                print("processed_emails received", processed_emails)
                retrieved_messages = mailbox.fetch(A(seen=False, from_=CAD_EMAIL_ADDRESS, subject=SUBJECT_PREFIX, date_gte=start_time), mark_seen=False)
                for msg in retrieved_messages:
                    # Check if we've already processed the email, if not, process it
                    if msg.uid not in processed_emails:
                        save_processed_email(msg.uid)
                        handle_email(msg, mailbox)
    except Exception as e:
        traceback.print_exc()
        display_message("Email Login Error", .3)

def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)

    print("\nQuitting...")
    sys.exit(1)

if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    run_program()
