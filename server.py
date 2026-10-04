#!/usr/bin/env python3
"""Local game server with validated config saving and registration routes."""
import argparse, json, math, os, tempfile, socket
from pathlib import Path
from urllib.parse import urlsplit, unquote
import registration
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
DEFAULT_SETTINGS = dict(hitMode='body', hitRadius=.09, itemScale=1, maxActiveItems=2,
                        startMode='hand', startHand='either', holdSeconds=2, showBodyLines=False)

def validate_config(data):
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('coordinateSystem') != 'normalized' or data.get('reference') != 'game-camera':
        raise ValueError('Invalid config format')
    zones = data.get('zones')
    if not isinstance(zones, list) or len(zones) != 6:
        raise ValueError('Six zones required')
    normalized = []
    def numeric(value, low, high):
        return type(value) in (int, float) and math.isfinite(value) and low <= value <= high
    for index in range(1, 7):
        matches = [z for z in zones if isinstance(z, dict) and z.get('id') == f'Z{index}']
        if len(matches) != 1 or not all(numeric(matches[0].get(k), 0, 1) for k in ('x', 'y')):
            raise ValueError('Invalid zone coordinates')
        normalized.append({key: matches[0][key] for key in ('id', 'x', 'y')})
    supplied = data.get('settings', {})
    if not isinstance(supplied, dict): raise ValueError('Invalid settings')
    settings = {key: supplied.get(key, default) for key, default in DEFAULT_SETTINGS.items()}
    if (settings['hitMode'] not in ('body', 'feet') or
        not numeric(settings['hitRadius'], .04, .18) or
        not numeric(settings['itemScale'], .7, 1.5) or
        type(settings['maxActiveItems']) is not int or not 1 <= settings['maxActiveItems'] <= 3 or
        settings['startMode'] not in ('hand', 'body') or settings['startHand'] not in ('either', 'left', 'right') or
        not numeric(settings['holdSeconds'], .5, 5) or type(settings['showBodyLines']) is not bool):
        raise ValueError('Settings out of range')
    return dict(version=1, coordinateSystem='normalized', reference='game-camera', settings=settings, zones=normalized)

def write_config(root, data):
    valid = validate_config(data)
    folder = root / 'config'; folder.mkdir(exist_ok=True)
    path = folder / 'zones.json'; temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=folder, prefix='.zones-', delete=False) as output:
            temporary = Path(output.name)
            json.dump(valid, output, ensure_ascii=False, indent=2, allow_nan=False); output.write('\n')
            output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists(): temporary.unlink()

class GameHandler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=str(server.root))
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def reply(self,status,payload,cookie=None):
        body=json.dumps(payload,ensure_ascii=False).encode('utf-8'); self.send_response(status)
        if cookie:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if registration.get(self): return
        path=urlsplit(self.path).path
        if path=='/config/zones.json':
            try:
                body=(self.server.root/'config/zones.json').read_bytes()
                self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            except FileNotFoundError:self.reply(404,{'error':'not found'})
            return
        super().do_GET()
    def do_POST(self):
        if registration.post(self): return
        if urlsplit(self.path).path!='/api/config': self.reply(404,{'error':'not found'});return
        try:
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json': raise ValueError('JSON required')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32768: raise ValueError('Invalid request size')
            self.connection.settimeout(5); data=json.loads(self.rfile.read(length)); write_config(self.server.root,data)
            self.reply(200,{'saved':True})
        except (ValueError,json.JSONDecodeError) as exc:self.reply(400,{'error':str(exc)})
        except Exception as exc:self.reply(500,{'error':'save failed','detail':str(exc)})

def registration_url(host,port):
    public=os.environ.get('STOMP_PUBLIC_URL','').rstrip('/')
    if public:return public+'/register.html'
    return f'http://{host}:{port}/register.html'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=ThreadingHTTPServer((args.host,args.port),GameHandler);server.root=ROOT
    server.registration_url=registration_url(args.host,args.port)
    print(f'Smooth Stomp: http://{args.host}:{args.port}/')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
