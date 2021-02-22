import os
import sys
import time
import xkcd
import queue
import signal
import logging
import pathlib
import pyqrcode
import threading
from utils import image
from threading import Lock
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, jsonify, current_app
from displays.epaper.waveshare import waveshare_7in5_v2

app = Flask(__name__)

DIR_TMP = 'tmp'
DIR_RES = 'res'

TASK_PRIO_TERMINATE = 0
TASK_PRIO_DISPLAY_QR_WIFI = 2
TASK_PRIO_UPDATE_COMIC_PERIODIC = 1

TASK_ID_INVALID = -1
TASK_ID_TERMINATE = 1
TASK_ID_DISPLAY_QR_WIFI = 2
TASK_ID_UPDATE_COMIC_PERIODIC = 3

# WiFi credentials for generating QR code.
TASK_DISPLAY_QR_WIFI_PSK = None
TASK_DISPLAY_QR_WIFI_SSID = None
TASK_DISPLAY_QR_WIFI_PROTOCOL = "WPA/WPA2"

TIMEOUT_SEC_DISPLAY_QR_WIFI = 120.0
INTERVAL_SEC_UPDATE_COMIC_PERIODIC = 21600.0

logging.basicConfig(
    level = logging.DEBUG,
    datefmt = "%d-%m-%Y %H:%M:%S",
    format = "%(asctime)s papycast :: %(filename)s :: %(levelname)s: %(message)s"
)

# The signal handler.
def handler_sigint(signal_number, frame):
    logging.debug('Interrupt signal (CTRL+C) handler')

    if thread_task_handler.is_alive():
        logging.debug('Main thread is alive, attempting to end the main thread')

        queue_task_handler.put(
            (
                TASK_PRIO_TERMINATE,
                {
                    id: TASK_ID_TERMINATE
                }
            )
        )

        logging.debug('Task queued, waiting for the main thread to join')

        thread_task_handler.join()

        logging.debug('Main thread joined')

    logging.debug('Interrupt signal handled')

    exit(0)

# Main thread function.
def thread_task_handler():
    timer_update_comic_periodic = None

    def enqueue_task_update_comic_periodic(queue_task_handler):
        queue_task_handler.put(
            (
                TASK_PRIO_UPDATE_COMIC_PERIODIC,
                {
                    id: TASK_ID_UPDATE_COMIC_PERIODIC
                }
            )
        )

    def do_display(display, image):
        display.init()

        display.do_clear()

        display.display(display.get_image_buffer(image))

        time.sleep(2)

        display.do_sleep()

    while(True):
        logging.debug('main_thread: Waiting for new tasks')

        _, task = queue_task_handler.get()

        if (timer_update_comic_periodic != None) and timer_update_comic_periodic.is_alive():
            timer_update_comic_periodic.cancel()

        try:
            # Task: Terminate.
            if task[id] == TASK_ID_TERMINATE:
                logging.info(
                    "main_thread: Terminating, current queue size = %d" %
                    queue_task_handler.qsize()
                )

                break

            # Task: Display QR encoded WiFi credentials.
            if task[id] == TASK_ID_DISPLAY_QR_WIFI:
                logging.info("main_thread: Display QR encoded WiFi credentials")

                qr_wifi = pyqrcode.create(
                    F'WIFI:S:{TASK_DISPLAY_QR_WIFI_SSID};T:{TASK_DISPLAY_QR_WIFI_PROTOCOL};P:{TASK_DISPLAY_QR_WIFI_PSK};'
                )

                qr_wifi.png(
                    os.path.join(DIR_TMP, 'current_image_raw.png'),
                    scale = 8,
                    module_color = [0, 0, 0, 255],
                    background = [0xff, 0xff, 0xff]
                )

                current_image_raw = Image.open(os.path.join(DIR_TMP, 'current_image_raw.png'))

                current_image_raw = current_image_raw.resize((400, 400))

                current_image_raw = image.do_center(
                    current_image_raw,
                    Image.open(os.path.join(DIR_RES, 'img/bg_screen_800_480.png')),
                    waveshare_7in5_v2
                )

                if current_image_raw == None:
                    logging.error("main_thread: Failed to center generated WiFi QR code")
                else:
                    current_image_raw.save(
                        os.path.join(DIR_TMP, 'current_image.bmp'),
                        'BMP'
                    )

                    current_image = Image.open(os.path.join(DIR_TMP, 'current_image.bmp'))

                    do_display(waveshare_7in5_v2.Waveshare7in5V2(), current_image)

                    time.sleep(TIMEOUT_SEC_DISPLAY_QR_WIFI)

                    with app.app_context():
                        with current_app.app_lock:
                            current_app.is_handling_task_display_qr_wifi = False

                    task[id] = TASK_ID_UPDATE_COMIC_PERIODIC

            # Task: (Periodic) Update comic.
            if task[id] == TASK_ID_UPDATE_COMIC_PERIODIC:
                attempt = 1
                found_comic = False

                while(not found_comic):
                    logging.info(
                        "main_thread: Getting new comic, attempt number %d" %
                        attempt
                    )

                    comic = xkcd.getRandomComic()

                    comic.download(
                        silent = False,
                        output = DIR_TMP,
                        outputFile = 'current_image_raw.png'
                    )

                    current_image_raw = \
                        Image.open(os.path.join(DIR_TMP, 'current_image_raw.png'))

                    current_image_raw_w, current_image_raw_h = \
                        current_image_raw.size

                    attempt += 1

                    if (current_image_raw_w <= waveshare_7in5_v2.WIDTH) \
                        and \
                        (current_image_raw_h <= waveshare_7in5_v2.HEIGHT):
                            found_comic = True

                logging.info(
                    "main_thread: Got new comic, image dimension = %s" %
                    str(current_image_raw.size)
                )

                current_image_raw = \
                    current_image_raw.resize(
                        (waveshare_7in5_v2.WIDTH, waveshare_7in5_v2.HEIGHT)
                    )

                current_image_raw.save(
                    os.path.join(DIR_TMP, 'current_image.bmp'),
                    'BMP'
                )

                current_image = Image.open(os.path.join(DIR_TMP, 'current_image.bmp'))

                do_display(waveshare_7in5_v2.Waveshare7in5V2(), current_image)
        except Exception as e:
            logging.error(repr(e))
        finally:
            timer_update_comic_periodic = \
                threading.Timer(
                    INTERVAL_SEC_UPDATE_COMIC_PERIODIC,
                    enqueue_task_update_comic_periodic,
                    args = [queue_task_handler]
                )

            timer_update_comic_periodic.start()

# Flask stuff.

with app.app_context():
    current_app.app_lock = Lock()

    with current_app.app_lock:
        current_app.is_handling_task_display_qr_wifi = False

# REST endpoints.

# Periodic comic updates.
@app.route('/update_comic')
def ep_update_comic():
    if not thread_task_handler.is_alive():
        return jsonify(id = TASK_ID_UPDATE_COMIC_PERIODIC, status = -1)

    queue_task_handler.put(
        (
            TASK_PRIO_UPDATE_COMIC_PERIODIC,
            {
                id: TASK_ID_UPDATE_COMIC_PERIODIC
            }
        )
    )

    return jsonify(id = TASK_ID_UPDATE_COMIC_PERIODIC, status = 0)

# Display WiFi credentials as QR code.
@app.route('/display_qr_wifi')
def ep_display_qr_wifi():
    with app.app_context():
        with current_app.app_lock:
            if not thread_task_handler.is_alive() or current_app.is_handling_task_display_qr_wifi:
                return jsonify(id = TASK_ID_DISPLAY_QR_WIFI, status = -1)

            current_app.is_handling_task_display_qr_wifi = True

            queue_task_handler.put(
                (
                    TASK_PRIO_DISPLAY_QR_WIFI,
                    {
                        id: TASK_ID_DISPLAY_QR_WIFI
                    }
                )
            )

    return jsonify(id = TASK_ID_DISPLAY_QR_WIFI, status = 0)

# Application main.

if __name__ == '__main__':
    if ('PAPYCAST_ENV_QR_WIFI_SSID' not in os.environ) or \
       ('PAPYCAST_ENV_QR_WIFI_SSID_PSK' not in os.environ):
            sys.exit("\nThe following environment variables must be set:\n\n\
1. PAPYCAST_ENV_QR_WIFI_SSID\n2. PAPYCAST_ENV_QR_WIFI_SSID_PSK\n")

    TASK_DISPLAY_QR_WIFI_SSID = \
        os.environ['PAPYCAST_ENV_QR_WIFI_SSID']

    TASK_DISPLAY_QR_WIFI_PSK = \
        os.environ['PAPYCAST_ENV_QR_WIFI_SSID_PSK']

    if TASK_DISPLAY_QR_WIFI_SSID == '' or TASK_DISPLAY_QR_WIFI_PSK == '':
        sys.exit("\nThe following environment variables must be set:\n\n\
1. PAPYCAST_ENV_QR_WIFI_SSID\n2. PAPYCAST_ENV_QR_WIFI_SSID_PSK\n")

    # Register signal handler.
    signal.signal(signal.SIGINT, handler_sigint)

    # Create the temporary directory if it's not there.
    pathlib.Path(DIR_TMP).mkdir(parents = False, exist_ok = True)

    # Prepare and start the main thread.
    queue_task_handler = queue.PriorityQueue(maxsize = 0)

    thread_task_handler = \
        threading.Thread(
            args = (),
            name = 'Task Handler',
            target = thread_task_handler
        )

    thread_task_handler.start()

    # Get started with periodic comic update.
    queue_task_handler.put(
        (
            TASK_PRIO_UPDATE_COMIC_PERIODIC,
            {
                id: TASK_ID_UPDATE_COMIC_PERIODIC
            }
        )
    )

    # Start Flask application.
    app.run(debug = False, host = '0.0.0.0')
