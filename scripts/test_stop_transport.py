"""Exercise the real PowerShell interrupt client against a local fake app-server."""
import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
import powershell_host
from windows_process import hidden_options


def exact(connection,size):
    data=b''
    while len(data)<size:
        chunk=connection.recv(size-len(data))
        if not chunk:raise EOFError()
        data+=chunk
    return data


def receive(connection):
    header=exact(connection,2)
    if header[0]&15==8:raise EOFError()
    size=header[1]&127
    if size==126:size=struct.unpack('!H',exact(connection,2))[0]
    elif size==127:size=struct.unpack('!Q',exact(connection,8))[0]
    mask=exact(connection,4) if header[1]&128 else None
    payload=exact(connection,size)
    if mask:payload=bytes(value^mask[index%4] for index,value in enumerate(payload))
    return json.loads(payload)


def send(connection,payload):
    data=json.dumps(payload).encode()
    header=bytes([129,len(data)]) if len(data)<126 else bytes([129,126])+struct.pack('!H',len(data))
    connection.sendall(header+data)


@unittest.skipUnless(os.name=='nt','PowerShell WebSocket transport')
class StopTransportTests(unittest.TestCase):
    def exercise(self,active):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(10)
        port=listener.getsockname()[1];requests=[];errors=[]
        def server():
            try:
                connection,_=listener.accept()
                with connection:
                    connection.settimeout(8);headers=b''
                    while not headers.endswith(b'\r\n\r\n'):headers+=exact(connection,1)
                    values=dict(line.split(': ',1) for line in headers.decode().split('\r\n')[1:] if ': ' in line)
                    key=values['Sec-WebSocket-Key']
                    accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                    connection.sendall(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n').encode())
                    while True:
                        request=receive(connection);requests.append(request)
                        method=request['method']
                        if method=='initialize':send(connection,dict(id=request['id'],result={}))
                        elif method=='thread/read':
                            turns=[dict(id='old-turn',status='completed')]
                            if active:turns.append(dict(id='resumed-turn',status='inProgress'))
                            send(connection,dict(id=request['id'],result=dict(thread=dict(turns=turns))))
                        elif method=='turn/interrupt':
                            send(connection,dict(id=request['id'],result={}))
                            send(connection,dict(method='turn/completed',params=dict(turn=dict(id='resumed-turn',status='interrupted'))))
            except EOFError:pass
            except Exception as exc:errors.append(str(exc))
            finally:listener.close()
        worker=threading.Thread(target=server,daemon=True);worker.start()
        with tempfile.TemporaryDirectory() as folder:
            binding=Path(folder)/'binding.json'
            binding.write_text(json.dumps(dict(kind='app_server',url=f'ws://127.0.0.1:{port}',thread_id='bound-thread',turn_id='old-turn')),encoding='utf-8')
            command=powershell_host.command(Path(__file__).with_name('app-server-stop.ps1'),'-Binding',binding,'-Action','Stop')
            result=subprocess.run(command,capture_output=True,timeout=10,**hidden_options())
        worker.join(2)
        self.assertFalse(errors,errors)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        self.assertTrue(result.stdout.decode('utf-8-sig').strip().startswith('{'),dict(stdout=repr(result.stdout),stderr=result.stderr.decode('utf-8',errors='replace'),requests=requests))
        return json.loads(result.stdout.decode('utf-8-sig')),requests

    def test_resume_interrupts_new_active_turn_on_the_bound_thread(self):
        result,requests=self.exercise(True)
        self.assertEqual(result['state'],'interrupted')
        interrupt=[r for r in requests if r['method']=='turn/interrupt']
        self.assertEqual(interrupt[0]['params'],dict(threadId='bound-thread',turnId='resumed-turn'))

    def test_idle_thread_requires_no_interrupt(self):
        result,requests=self.exercise(False)
        self.assertEqual(result['state'],'idle')
        self.assertFalse(any(r['method']=='turn/interrupt' for r in requests))


if __name__=='__main__':unittest.main()
