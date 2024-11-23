# fd_signage

This repository contains scripts for displaying messages on an LED matrix using emails as the source of the messages. The main functionality is implemented in [`display-email.py`](display-email.py), while [`display-message.py`](display-message.py) serves as a simple test script.

## Requirements

- Python 3.x
- `rgbmatrix` library
- `imap_tools` library
- `beautifulsoup4` library
- `dotenv` library
- LED matrix hardware (configured for Adafruit HAT)

## Prerequisites

- Switch off on-board sound on raspberry pi (dtparam=audio=off in /boot/config.txt)
- Do not use graphical user interface

## Installation

1. Install the rpi-rbg-led-matrix library.
    Follow the instructions on their site here: https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/bindings/python
    - Clone https://github.com/hzeller/rpi-rgb-led-matrix.git
    - Edit the lib/Makefile, line 37 to say `HARDWARE_DESC?=adafruit-hat`
    - Run:
    ```sh
    sudo apt-get update && sudo apt-get install python3-dev cython3 -y
    make build-python 
    sudo make install-python 
    ```

2. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/fd_signage.git
    cd fd_signage
    ```

3. Install the required Python packages:
    ```sh
    sudo apt install python3-imap_tools
    sudo apt install python3-beautifulsoup4
    sudo apt install python3-dotenv
    ```

4. Set up your environment variables in a `.env` file:
    ```env
    EMAIL_ADDRESS=your_email@example.com
    EMAIL_PASSWORD=your_password
    EMAIL_HOST=your_email_host
    ```

## Usage

### Running As A Service

This has been configured to run as a systemd service. This means that when enabled, the program will automatically start on device boot. If changes are made to the script, then you will need to run `./refresh-service.sh` to update that with the latest code.

Attached are some other helpful commands relating to this service:

```sh
# View Logs
journalctl -u sign.service
journalctl -u sign.service -n 100 -f

# Temporarily Turn off service
sudo systemctl stop sign.service

# Turn back on (after temporarily turned off)
sudo systemctl start

# Enable Service
sudo systemctl enable sign.service
sudo reboot

# Disable Service
sudo systemctl enable sign.service
sudo reboot
```

#### Setting up Systemd Service

```sh
sudo cp service/sign.service /lib/systemd/system/sign.service
sudo chmod 644 /lib/systemd/system/sign.service
sudo systemctl daemon-reload
sudo systemctl enable sample.service
# Reboot may be needed on the first time to see the service start up
sudo reboot
```

### Running the Main Script

The main script, [`display-email.py`](display-email.py), checks for new emails and displays messages on the LED matrix.

1. Ensure your environment variables are set up in the `.env` file.
2. Run the script:

    ```sh
    sudo ./display-email.py
    ```

### Running the Test Script

The test script, [`display-message.py`](display-message.py), displays a hardcoded message on the LED matrix for testing purposes.

1. Run the script:

    ```sh
    sudo ./display-message.py
    ```

## Fonts

The fonts used for displaying messages are located in the [`fonts`](fonts) directory. These are BDF fonts, a simple bitmap font format suitable for low-resolution screens like LED displays. Future work may be editing one of these to create a font that perfectly fits our 16x32 matrix panels

For more information on the provided fonts and how to create your own, refer to the [`fonts/README.md`](fonts/README.md) file.

## License

This repository uses fonts that are public domain, except for `tom-thumb.bdf`, which is under the MIT license. For more details, see the [`fonts/README.md`](fonts/README.md) file. The rest of the code in this repository is licensed under the MIT License.
