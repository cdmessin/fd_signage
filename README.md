# fd_signage

This repository contains a program to be used by a volunteer fire department for displaying messages on an LED matrix using dispatch emails as the source of the messages. The python script created is specific to the emails being sent while this was implemented. The main functionality is implemented in [`display-email.py`](display-email.py), while [`display-message.py`](display-message.py) serves as a simple test script.

This readme contains information on the entire project setup which results in a raspberry pi which upon boot:
- Connects to the configured wifi network
- Automatically starts up the service to check for emails
- When an valid email comes in, displays the incident type and address on the LED Matrix for 3 minutes

## Requirements

- Python 3.x
- `rgbmatrix` library
- `imap_tools` library
- `beautifulsoup4` library
- `dotenv` library
- LED matrix hardware (configured for Adafruit HAT)
    - 4 [16x32 LED Matrix Panels - 6mm pitch](https://www.adafruit.com/product/420) (Each comes with a single GPIO ribbon and a power cable that can supply 2 panels)
    - 2 [Female DC Power Adapters - 2.1mm jack to screw terminal block](https://www.adafruit.com/product/368)
    - 1 [Adadfruit RGB Matrix Bonnet for Raspberry Pi](https://www.adafruit.com/product/3211)
    - 2 5V 4A Power Supply (Power Configuration was setup following [this guide here](https://learn.adafruit.com/led-matrix-sports-scoreboard/wiring-and-assembly#power-3154589))

## Prerequisites

- This was coded for a Raspberry Pi 3B, performance has not been tested on other models
- Raspberry Pi was Imaged with Raspberry Pi OS Bookworm. The remainder of the README assumes this is the OS that is being used for this setup. There are some steps that are specific to bookworm.
- Switch off on-board sound on raspberry pi. Edit `/boot/config.txt` and set `dtparam=audio=off`
- Do not use graphical user interface. Change to headless mode to save on processing.
- Original wifi network was setup in [imager](https://www.raspberrypi.com/software/). Additional wifi was set up for use in a new location `sudo nmtui edit`

### Wifi Setup

On the Bookworm OS, nmtui and nmcli are the main network managers.
The initial wifi network is configured using the [imager](https://www.raspberrypi.com/software/), however we need to configure this to automatically connect to other wifi networks.

1. Run `sudo nmtui edit` to open a graphical command line program where you can add wifi networks.
2. Set the wifi connection priority using nmcli:

```sh
# List the connections set
sudo nmcli --fields autoconnect-priority,name connection
# Set the priority for each connection. Higher numbers mean higher priority
sudo nmcli connection modify "<connection_name_here>" connection.autoconnect-priority <priority_integer>
```

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
sudo systemctl start sign.service

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

The fonts used for displaying messages are located in the [`fonts`](fonts) directory. These are BDF fonts, a simple bitmap font format suitable for low-resolution screens like LED displays. The sepecific font we are using is "Better VCR" taken from dafont.com and translated into a bdf font using the tool referenced in the [`fonts/README.md`](fonts/README.md) file like so:
`otf2bdf -v -o myfont.bdf ./fd_signage/fonts/ttf/Better\ VCR\ 6.1.ttf`

For more information on the provided fonts and how to create your own, refer to that same [`fonts/README.md`](fonts/README.md) file.

## License

This repository uses fonts that are public domain, except for `tom-thumb.bdf`, which is under the MIT license. For more details, see the [`fonts/README.md`](fonts/README.md) file. The rest of the code in this repository is licensed under the MIT License.
