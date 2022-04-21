from .javascript import init_notebook_mode, show
from .version import __version__

__all__ = ["__version__", "show", "init_notebook_mode"]


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "jupyterlab-itables"}]
