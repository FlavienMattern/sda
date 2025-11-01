# This __init__.py file imports the main function from main.py directly via a wrapper
from pathlib import Path
import importlib

# Module name based on the file name
_module_name = Path(__file__).parent.name

# Import the function in main.py with the same name as the module
_main_module = importlib.import_module(".main", package=__package__)
_main_func = getattr(_main_module, _module_name)

# Define wrapper
def _create_wrapper(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

globals()[_module_name] = _create_wrapper(_main_func)
__all__ = [_module_name]
del Path, importlib, _module_name, _main_module, _main_func, _create_wrapper