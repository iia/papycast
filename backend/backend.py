import os
import time
import xkcd
import queue
import signal
import logging
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
TASK_DISPLAY_QR_WIFI_SSID = 'LisIsh@Guest'
TASK_DISPLAY_QR_WIFI_PROTOCOL = 'WPA/WPA2'
TASK_DISPLAY_QR_WIFI_PSK = 'you_are_welcome'

TIMEOUT_SEC_DISPLAY_QR_WIFI = 120.0
INTERVAL_SEC_UPDATE_COMIC_PERIODIC = 21600.0

logging.basicConfig(
    level = logging.DEBUG,
    datefmt = "%d-%m-%Y %H:%M:%S",
    format = "%(asctime)s papycast :: %(filename)s :: %(levelname)s: %(message)s"
)

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
                    os.path.join(DIR_TMP, 'qr_wifi_raw.png'),
                    scale = 8,
                    module_color = [0, 0, 0, 255],
                    background = [0xff, 0xff, 0xff]
                )

                qr_wifi_raw = Image.open(os.path.join(DIR_TMP, 'qr_wifi_raw.png'))

                qr_wifi_raw_resized = qr_wifi_raw.resize((400, 400))

                qr_wifi_raw_resized_centered = image.do_center(
                    qr_wifi_raw_resized,
                    Image.open(os.path.join(DIR_RES, 'img/bg_screen_800_480.png')),
                    waveshare_7in5_v2
                )

                if qr_wifi_raw_resized_centered == None:
                    logging.error("main_thread: Failed to center generated WiFi QR code")
                else:
                    qr_wifi_raw_resized_centered.save(
                        os.path.join(DIR_TMP, 'qr_wifi.bmp'),
                        'BMP'
                    )

                    image_qr_wifi = Image.open(os.path.join(DIR_TMP, 'qr_wifi.bmp'))

                    do_display(waveshare_7in5_v2.Waveshare7in5V2(), image_qr_wifi)

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
                        outputFile = 'xkcd_raw.png'
                    )

                    image_xkcd_raw = \
                        Image.open(os.path.join(DIR_TMP, 'xkcd_raw.png'))

                    image_xkcd_raw_w, image_xkcd_raw_h = \
                        image_xkcd_raw.size

                    attempt += 1

                    if (image_xkcd_raw_w <= waveshare_7in5_v2.WIDTH) \
                    and \
                    (image_xkcd_raw_h <= waveshare_7in5_v2.HEIGHT):
                        found_comic = True

                logging.info(
                    "main_thread: Got new comic, image dimension = %s" %
                    str(image_xkcd_raw.size)
                )

                image_xkcd_raw = Image.open(os.path.join(DIR_TMP, 'xkcd_raw.png'))

                image_xkcd_raw_resized = \
                    image_xkcd_raw.resize(
                        (waveshare_7in5_v2.WIDTH, waveshare_7in5_v2.HEIGHT)
                    )

                image_xkcd_raw_resized.save(
                    os.path.join(DIR_TMP, 'xkcd.bmp'),
                    'BMP'
                )

                image_xkcd = Image.open(os.path.join(DIR_TMP, 'xkcd.bmp'))

                do_display(waveshare_7in5_v2.Waveshare7in5V2(), image_xkcd)
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

with app.app_context():
    current_app.app_lock = Lock()

    with current_app.app_lock:
        current_app.is_handling_task_display_qr_wifi = False

queue_task_handler = queue.PriorityQueue(maxsize = 0)

thread_task_handler = \
    threading.Thread(
        args = (),
        name = 'Task Handler',
        target = thread_task_handler
    )

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

signal.signal(signal.SIGINT, handler_sigint)

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
