from .main import run

class Wrapper:
    def __call__(self, *args, **kwargs):
        return run(*args, **kwargs)

scan_data = Wrapper()