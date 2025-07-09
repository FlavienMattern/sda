from .main import ppsd as main

def ppsd(*args, **kwargs):
    return main(*args, **kwargs)

__all__ = ["ppsd"]