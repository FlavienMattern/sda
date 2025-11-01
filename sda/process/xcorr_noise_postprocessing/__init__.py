from .main import xcorr_noise_postprocessing as main

def xcorr_noise_postprocessing(*args, **kwargs):
    return main(*args, **kwargs)

__all__ = ["xcorr_noise_postprocessing"]