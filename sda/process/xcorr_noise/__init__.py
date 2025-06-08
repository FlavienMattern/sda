from .main import xcorr_noise as main

def xcorr_noise(*args, **kwargs):
    return main(*args, **kwargs)

__all__ = ["xcorr_noise"]