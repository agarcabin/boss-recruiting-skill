"""Best-effort asynchronous Windows error sound, with bounded repeats."""
import threading
import time

_lock=threading.Lock()
_last=None


def play():
    global _last
    with _lock:
        now=time.monotonic()
        if _last is not None and now-_last<5:return
        _last=now
    try:
        import winsound
        winsound.PlaySound('SystemHand',winsound.SND_ALIAS|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
    except (ImportError,RuntimeError,OSError):
        pass
