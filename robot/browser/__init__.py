import logging
import threading

from os.path import join


from .events_hmV2 import *
from .events_zaraV2 import *
from .events_eta import *
from .events_deprati import *


def browsing_session():
    logging.info("Browsing session started.")

    hm_session = hmSession()
    zara_session = zaraSession()
    eta_session = etaSession()
    deprati_session = depratiSession()

    sessions = [
        deprati_session.start_scrapping
    ]

    semaphore = threading.Semaphore(4)
    threads = []
    for session in sessions:
        thread = threading.Thread(target=session, args=([semaphore]))
        thread.start()
        threads.append(thread)
        
    for t in threads:
        t.join()
        
    logging.info("Browsing session finished.")