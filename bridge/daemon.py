import logging
import sys
import signal
import threading
from functools import partial

from bridge.backend_handler import BackendHandler
from bridge import settings
from bridge.judge_handler import JudgeHandler
from bridge.judge_list import JudgeList
from bridge.server import Server
from bridge.models import Judge, Submission

logger = logging.getLogger('judge.bridge')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def reset_judges():
    Judge.update(online=False, ping=None, load=None).execute()


def judge_daemon():
    logger.info('Starting judge bridge')
    reset_judges()
    Submission.update(status='IE', result='IE', error=None)\
        .where(Submission.status.in_(('QU', 'G', 'P'))).execute()

    judges = JudgeList()

    judge_server = Server(settings["judge"], partial(JudgeHandler, judges=judges))
    backend_server = Server(settings["backend"], partial(BackendHandler, judges=judges))

    threading.Thread(target=backend_server.serve_forever).start()
    threading.Thread(target=judge_server.serve_forever).start()

    stop = threading.Event()

    def signal_handler(signum, _):
        logger.info('Exiting due to %s', signal.Signals(signum).name)
        stop.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        stop.wait()
    finally:
        backend_server.shutdown()
        judge_server.shutdown()
