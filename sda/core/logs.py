import logging
import logging.handlers
import multiprocessing as mp
import os
import sys
from datetime import datetime


# Global variables
_log_queue = None
_listener_process = None
_log_initialized = False
_log_level = logging.INFO


# Functions
def _get_main_script_name():
    main_script = os.path.basename(sys.argv[0])
    return os.path.splitext(main_script)[0] or "main"


def _listener_configurer(log_dir):
    # Logfile initiation
    os.makedirs(log_dir, exist_ok=True)
    log_name = _get_main_script_name()
    log_file = os.path.join(log_dir, f"{log_name}_{datetime.now():%Y-%m-%d_%H%M%S}.log")

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
    
    logging.info(f"Started logging to {log_file}")


def _listener_process_main(queue, log_dir):
    # Logs recovery and writing
    _listener_configurer(log_dir)
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


def start_logging(log_dir="logs", level="INFO"):
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

    level = level.upper()
    if not hasattr(logging, level):
        raise ValueError(f"Wrong logging level : {level}")
    _log_level = getattr(logging, level)

    _log_queue = mp.Queue()
    _listener_process = mp.Process(
        target=_listener_process_main, args=(_log_queue, log_dir), daemon=True
    )
    _listener_process.start()
    _log_initialized = True


def stop_logging():
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
    _worker_configurer()

    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(message)
