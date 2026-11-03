"""Bounded cross-process mutexes. Kernel ownership is released on process death."""
import contextlib,ctypes,hashlib,os,tempfile,time
from pathlib import Path

@contextlib.contextmanager
def locked(key,timeout=25):
    name=hashlib.sha256(str(key).encode('utf-8')).hexdigest()
    if os.name=='nt':
        from ctypes import wintypes
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        api.CreateMutexW.restype=wintypes.HANDLE
        api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        api.ReleaseMutex.argtypes=[wintypes.HANDLE];api.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=api.CreateMutexW(None,False,'Local\\Recruiting_'+name)
        if not handle:raise OSError(ctypes.get_last_error(),'CreateMutex')
        acquired=api.WaitForSingleObject(handle,int(timeout*1000)) in (0,0x80)
        try:
            if not acquired:raise TimeoutError('local_mutex_timeout')
            yield
        finally:
            if acquired:api.ReleaseMutex(handle)
            api.CloseHandle(handle)
    else:
        import fcntl
        with open(Path(tempfile.gettempdir())/('recruiting-'+name+'.lock'),'a') as stream:
            until=time.monotonic()+timeout
            while True:
                try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>until:raise TimeoutError('local_mutex_timeout')
                    time.sleep(.05)
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)
