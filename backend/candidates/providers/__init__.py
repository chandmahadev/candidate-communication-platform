import threading

from django.conf import settings
from django.utils.module_loading import import_string

_instances = {}
_instances_lock = threading.Lock()


def get_provider():
    """Return the shared instance of the provider configured in settings.MESSAGING_PROVIDER."""
    path = settings.MESSAGING_PROVIDER
    with _instances_lock:
        if path not in _instances:
            _instances[path] = import_string(path)()
        return _instances[path]
