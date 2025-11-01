from .main import scan_data as main

def scan_data(*args, **kwargs):
    return main(*args, **kwargs)

__all__ = ["scan_data"]