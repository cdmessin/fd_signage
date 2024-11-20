#!/usr/bin/env python
import signal
import time
import sys
import traceback
import datetime

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from imap_tools import MailBox, MailMessage, A, AND, OR, NOT, MailMessageFlags
from bs4 import BeautifulSoup
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

def display_message(message_text):
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
        message_end_time = time.time() + 60 * DISPLAY_TIME_MINS
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
    print('Unread Message Found:', msg.subject, msg.date)
    # Only process it if this is a valid incident report email
    if is_valid_email(msg):
        print("Message is valid incident")
        print("Marking message as read")
        mailbox.flag(msg.uid, MailMessageFlags.SEEN, True)
        att = msg.attachments[0]
        if '.eml' in att.filename:
            final_message = parse_email_attachment(att)
            display_message(final_message)
        else:
            print('Alert Received: No Email Attachment Found')
            display_message('Alert Received: No Email Attachment Found')

def is_valid_email(msg):
    # correct_sender = msg.from_ == CAD_EMAIL_ADDRESS
    # correct_subject = msg.subject.startswith(SUBJECT_PREFIX)
    attachement_available = len(msg.attachments) >= 1
    return attachement_available
    # return correct_sender and correct_subject and attachement_available

    # Parse the attached email. We expect there to always be 3 bold elements.


def parse_email_attachment(attachment):
    """ Parse the attached email. We expect there to always be 3 bold elements.
        
        The first bold element is "Communications"
        The second bold element is the Nature
        The thrid bold element is the Address
    """
    attached_email = MailMessage.from_bytes(attachment.payload)
    parsed_html = BeautifulSoup(attached_email.html, features="lxml")
    bold_elements = parsed_html.body.find_all('b')
    combined_message = bold_elements[1].text + " - " + bold_elements[2].text
    return combined_message

def run_program():
    if EMAIL_ADDRESS is None or EMAIL_HOST is None or EMAIL_PASSWORD is None:
	print("Unable to load environment variables")
	display_message("Unable to load environment variables")
	sys.exit(0)
    try:
        with MailBox(EMAIL_HOST).login(EMAIL_ADDRESS, EMAIL_PASSWORD) as mailbox:
            while True:
                print("Checking for email")
                time.sleep(5)
                retrieved_messages = mailbox.fetch(A(seen=False), mark_seen=True) #A(date=datetime.date(2024, 11, 17))
                for msg in retrieved_messages:
                    handle_email(msg, mailbox)
    except Exception as e:
        traceback.print_exc()
        display_message("Email Login Error")

def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)

    print("\nQuitting...")
    sys.exit(1)

if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    run_program()
