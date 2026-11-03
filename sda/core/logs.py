import logging
import logging.handlers
from loky.backend import get_context
import os
from datetime import datetime
import __main__


# Global variables
_log_queue = None
_listener_process = None
_log_initialized = False
_log_level = logging.INFO


# Functions
def _listener_configurer(log_path):
    # Logfile initiation
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    msg = r"""
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                                       
    ┃    _____ ____  _____    __    _____ _____ _____    ┃
    ┃   |   __|    \|  _  |  |  |  |     |   __|   __|   ┃
    ┃   |__   |  |  |     |  |  |__|  |  |  |  |__   |   ┃
    ┃   |_____|____/|__|__|  |_____|_____|_____|_____|   ┃
    ┃                                                    ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

    root = logging.getLogger()
    handler = logging.FileHandler(log_path, mode="a")
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] |%(processName)s| %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(_log_level)
    
    print(f"{datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')} Start logging to: {log_path}")
    logging.info(f"Start logging.")


def _listener_process_main(queue, log_path):
    # Logs recovery and writing
    _listener_configurer(log_path)
    while True:
        record = queue.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)
    logging.shutdown()


def _worker_configurer():
    # Queue handler
    root = logging.getLogger()
    if not any(isinstance(h, logging.handlers.QueueHandler) and h.queue is _log_queue
               for h in root.handlers):
        root.addHandler(logging.handlers.QueueHandler(_log_queue))
    root.setLevel(_log_level)


def get_worker_logging_config():
    return (_log_queue if _log_initialized else None, _log_level)


def init_worker_logging(queue, level):
    global _log_queue, _log_level, _log_initialized
    if queue is None:
        return
    _log_queue, _log_level = queue, level
    _worker_configurer()
    _log_initialized = True


def start_logging(log_path=None, level="INFO"):
    """
    Initiate logging.
    
    Parameters :
    -----------
    log_path : str or os.PathLike, optional
        Log file or directory. New paths without an extension are directories.
        Automatic filename: YYYY-MM-DD_hhmmss.log.
        Default directory: logs beside the running file.
    level : str
        Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    """
    global _log_queue, _listener_process, _log_initialized, _log_level
    if _log_initialized:
        return

    main_script = (
        getattr(__main__, "__file__", None)
        or getattr(__main__, "__vsc_ipynb_file__", None)
        or os.environ.get("JPY_SESSION_NAME")
    )
    if log_path is None:
        if not main_script or not os.path.isabs(main_script):
            raise ValueError("Cannot determine the script or notebook path. Specify log_path explicitly.")
        wdir = os.path.dirname(main_script)
        log_path = os.path.join(wdir, "logs")
    log_path = os.fspath(log_path)
    if os.path.isdir(log_path) or (not os.path.exists(log_path) and not os.path.splitext(os.path.basename(log_path))[1]):
        log_path = os.path.join(log_path, f"{datetime.now():%Y-%m-%d_%H%M%S}.log")
    log_path = os.path.abspath(log_path)

    level = level.upper()
    if not hasattr(logging, level):
        raise ValueError(f"Wrong logging level: {level}")
    _log_level = getattr(logging, level)

    context = get_context("loky")
    _log_queue = context.Queue()
    _listener_process = context.Process(
        target=_listener_process_main, args=(_log_queue, log_path), daemon=True
    )
    _listener_process.start()

    # configure once for this process
    _worker_configurer()

    _log_initialized = True
    add_log(f"File executed: {os.path.abspath(main_script)}" if main_script else "Interactive session.", level="info")


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
        return

    logger = logging.getLogger("sda")

    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(message)
