<p align="center">
    <img
        width="25%"
        style="text-align: center;"
        src=".github/res/img/papycast.svg" />
</p>

# Papycast

Papycast is one of my hobby projects for fun.

Current features of this project are:

1. Get a random comic from [xkcd](https://xkcd.com/) and display it on an e-paper display.

2. Update the comic every six hours.

3. The backend provides an end point: `/update_comic` which updates the comic on request.

4. Currently only [Waveshare 7.5 inch V2 e-paper display + HAT](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT) is supported.

> :warning: The project currently works only on Raspberry Pi with ARM v7.

## Usage

1. Clone this repository.

2. Make sure Python3, pip and Python3 virtual environment are installed:

```bash
$ sudo apt install python3 python3-pip python3-venv
```

3. Create a Python3 virtual environment:

```bash
$ python3 -m venv venv
```

4. Activate the Python3 virtual environment:

```bash
$ . venv/bin/activate
(venv)$
```

5. Install backend's Python3 requirements from within the Python3 virtual environment:

```bash
(venv)$ pip3 install -r requirements.txt
```

6. Run the backend:
```bash
(venv)$ ./start.sh
```

This script will start a [Flask](https://flask.palletsprojects.com/en/1.1.x/) application on port 5000 of the Raspberry Pi. There should already be a comic being displayed on the screen.

7. To request a comic update just use this URL: `http://<PI_IP>:5000/update_comic` from a web browser.
