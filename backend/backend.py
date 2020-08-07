import os
import time
import xkcd
import queue
import signal
import logging
import threading
from utils import image
from flask import Flask, jsonify
from PIL import Image,ImageDraw,ImageFont
from displays.epaper.waveshare import waveshare_7in5_v2

DIR_TMP = 'tmp'
DIR_RES = 'res'

TASK_PRIO_TERMINATE = 0
TASK_PRIO_UPDATE_COMIC_EP = 2
TASK_PRIO_UPDATE_COMIC_PERIODIC = 1

TASK_ID_TERMINATE = 1
TASK_ID_UPDATE_COMIC_EP = 3
TASK_ID_UPDATE_COMIC_PERIODIC = 2

INTERVAL_UPDATE_COMIC_PERIODIC = 21600.0

app = Flask(__name__)

logging.basicConfig(
    level = logging.DEBUG,
    datefmt = "%d-%m-%Y %H:%M:%S",
    format = "%(asctime)s papycast :: %(filename)s :: %(levelname)s: %(message)s"
)

def thread_task_handler(queue_task_handler):
    timer_update_comic_periodic = None

    def update_comic_periodic(queue_task_handler):
        queue_task_handler.put(
            (
                TASK_PRIO_UPDATE_COMIC_PERIODIC,
                {
                    id: TASK_ID_UPDATE_COMIC_PERIODIC
                }
            )
        )

    while(True):
        logging.debug('main_thread: Waiting for new tasks')

        _, task = queue_task_handler.get()

        if task[id] == TASK_ID_TERMINATE:
            logging.info(
                "main_thread: Terminating, current queue size = %d" %
                queue_task_handler.qsize()
            )

            timer_update_comic_periodic.cancel()

            break

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

        display = waveshare_7in5_v2.Waveshare7in5V2()

        display.init()

        display.do_clear()

        display.display(display.get_image_buffer(image_xkcd))

        time.sleep(2)

        display.do_sleep()

        if task[id] == TASK_ID_UPDATE_COMIC_PERIODIC:
            timer_update_comic_periodic = \
                threading.Timer(
                    INTERVAL_UPDATE_COMIC_PERIODIC,
                    update_comic_periodic,
                    args = [queue_task_handler]
                )

            timer_update_comic_periodic.start()

queue_task_handler = queue.PriorityQueue(maxsize = 0)

thread_task_handler = \
    threading.Thread(
        name = 'Task Handler',
        args = [queue_task_handler],
        target = thread_task_handler
    )

@app.route('/update_comic')
def ep_update_comic():
    if not thread_task_handler.is_alive():
        return jsonify(id = TASK_ID_UPDATE_COMIC_EP, status = -1)

    queue_task_handler.put(
        (
            TASK_PRIO_UPDATE_COMIC_EP,
            {
                id: TASK_ID_UPDATE_COMIC_EP
            }
        )
    )

    return jsonify(id = TASK_ID_UPDATE_COMIC_EP, status = 0)

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

queue_task_handler.put(
    (
        TASK_PRIO_UPDATE_COMIC_PERIODIC,
        {
            id: TASK_ID_UPDATE_COMIC_PERIODIC
        }
    )
)
