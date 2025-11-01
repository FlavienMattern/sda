import logging
import logging.handlers
import multiprocessing as mp
import os
import sys
from datetime import datetime
import __main__


# Global variables
_log_queue = None
_listener_process = None
_log_initialized = False
_log_level = logging.INFO


# Functions
def _get_main_script_name():
    main_script = os.path.basename(sys.argv[0])
    return os.path.splitext(main_script)[0] or "main"


def _listener_configurer(log_dir, log_name):
    # Logfile initiation
    os.makedirs(log_dir, exist_ok=True)
    if log_name is None:
        log_name = _get_main_script_name()
        log_file = os.path.join(log_dir, f"{log_name}_{datetime.now():%Y-%m-%d_%H%M%S}.log")
    else:
        log_file = os.path.join(log_dir, log_name)

    msg = """
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                                       
    ┃    _____ ____  _____    __    _____ _____ _____    ┃
    ┃   |   __|    \|  _  |  |  |  |     |   __|   __|   ┃
    ┃   |__   |  |  |     |  |  |__|  |  |  |  |__   |   ┃
    ┃   |_____|____/|__|__|  |_____|_____|_____|_____|   ┃
    ┃                                                    ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

    root = logging.getLogger()
    handler = logging.FileHandler(log_file, mode="a")
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(_log_level)
    
    print(f"{datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')} Start logging to: {log_file}")
    logging.info(f"Start logging.")


def _listener_process_main(queue, log_dir, log_name):
    # Logs recovery and writing
    _listener_configurer(log_dir, log_name)
    while True:
        record = queue.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)
    logging.shutdown()


def _worker_configurer():
    #Queue handler
    h = logging.handlers.QueueHandler(_log_queue)
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(_log_level)


def start_logging(log_dir=None, log_name=None, level="INFO"):
    """
    Initiate logging.
    
    Parameters :
    -----------
    level : str
        Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    """
    global _log_queue, _listener_process, _log_initialized, _log_level
    if _log_initialized:
        return

    if log_dir is None:
        wdir = os.path.dirname(os.path.abspath(__main__.__file__))
        log_dir = os.path.join(wdir, "logs")
        os.makedirs(log_dir, exist_ok=True)

    level = level.upper()
    if not hasattr(logging, level):
        raise ValueError(f"Wrong logging level: {level}")
    _log_level = getattr(logging, level)

    _log_queue = mp.Queue()
    _listener_process = mp.Process(
        target=_listener_process_main, args=(_log_queue, log_dir, log_name), daemon=True
    )
    _listener_process.start()

    # configure once for this process
    _worker_configurer()

    _log_initialized = True
    add_log(f"File executed: {os.path.abspath(__main__.__file__)}", level="info")


def stop_logging():
   
    add_log("Stop logging.", level="info")
    print(f"{datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')} Stop logging.")
    
    global _log_queue, _listener_process, _log_initialized
    if not _log_initialized:
        return
    _log_queue.put(None)
    _listener_process.join(timeout=2)
    _log_initialized = False
    


def add_log(message, level="info"):
    """
    Add a log message with a given level.
    
    Parameters :
    -----------
    message : str
        Log message.
    level : str
        Log level ("debug", "info", "warning", "error", "critical")
    """
    if not _log_initialized:
        start_logging()

    logger = logging.getLogger("sda")

    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(message)
