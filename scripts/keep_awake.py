"""Thread-owned Windows execution state, automatically released when the owner exits."""
import ctypes
import os


class KeepAwake:
    def __init__(self,apply=None):
        self.apply=apply or (ctypes.windll.kernel32.SetThreadExecutionState if os.name=='nt' else lambda flags:1)
        self.active=False

    def set_running(self,running):
        running=bool(running)
        if running==self.active: return
        flags=0x80000000 | (0x00000003 if running else 0)
        if not self.apply(flags): raise OSError('SetThreadExecutionState failed')
        self.active=running

    def close(self): self.set_running(False)
