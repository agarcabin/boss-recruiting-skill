"""Authenticated encryption, publisher signatures and user-bound Windows storage."""
import base64,ctypes,hashlib,json,os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes,serialization

def b64(value):return base64.b64encode(value).decode('ascii')
def raw(value):return base64.b64decode(value,validate=True)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def password_key(password,salt):
    if len(salt)!=16:raise ValueError('invalid_kdf_salt')
    return Scrypt(salt=salt,length=32,n=32768,r=8,p=1).derive(password.encode('utf-8'))
def legacy_key(value,salt):
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,info=b'recruiting-legacy-envelope/v1').derive(value)
def wrap(key,secret,aad):
    nonce=os.urandom(12)
    return dict(nonce=b64(nonce),wrapped=b64(AESGCM(key).encrypt(nonce,secret,aad)))
def unwrap(key,value,aad):
    nonce=raw(value['nonce']);cipher=raw(value['wrapped'])
    if len(nonce)!=12 or len(cipher)!=48:raise ValueError('invalid_key_envelope')
    return AESGCM(key).decrypt(nonce,cipher,aad)
def sign(value,private):
    return b64(Ed25519PrivateKey.from_private_bytes(private).sign(canonical(value)))
def verify(value,signature,public):
    Ed25519PublicKey.from_public_bytes(public).verify(raw(signature),canonical(value))

def protect(value):
    if os.name!='nt':raise RuntimeError('windows_dpapi_required')
    from ctypes import wintypes
    class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer=ctypes.create_string_buffer(value);source=Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    api=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32')
    api.CryptProtectData.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    if not api.CryptProtectData(ctypes.byref(source),'Recruiting local key',None,None,None,1,ctypes.byref(target)):raise OSError(ctypes.get_last_error(),'DPAPI protect')
    try:return ctypes.string_at(target.data,target.size)
    finally:kernel.LocalFree(target.data)

def unprotect(value):
    if os.name!='nt':raise RuntimeError('windows_dpapi_required')
    from ctypes import wintypes
    class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer=ctypes.create_string_buffer(value);source=Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    api=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32')
    api.CryptUnprotectData.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    if not api.CryptUnprotectData(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):raise OSError(ctypes.get_last_error(),'DPAPI unprotect')
    try:return ctypes.string_at(target.data,target.size)
    finally:kernel.LocalFree(target.data)

def atomic(path,data):
    from pathlib import Path
    import tempfile
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.sealed-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
