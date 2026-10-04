"""Registration storage and HTTP routes. Private records are never static files."""
import io, json, re, sqlite3, sys, uuid, os, secrets, time, threading
from contextlib import contextmanager
from http.cookies import SimpleCookie
from datetime import datetime, timezone
from urllib.parse import urlsplit

SESSION_LOCK=threading.Lock(); SESSIONS={}; SESSION_SECONDS=8*60*60
CONSENT_VERSION='event-draft-v1'
CONSENT_TEXT='ฉันยินยอมให้ผู้จัดกิจกรรมเก็บชื่อ นามสกุล และเบอร์โทร เพื่อจัดการลงทะเบียนและติดต่อเกี่ยวกับกิจกรรม Smooth Stomp นี้ ไม่รวมการติดต่อเพื่อการตลาด'

@contextmanager
def connect(root):
    folder=root/'data';folder.mkdir(exist_ok=True,mode=0o700)
    db=sqlite3.connect(folder/'registrations.sqlite3',timeout=10);db.row_factory=sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS registrations (
        queue INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
        request_id TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        phone TEXT NOT NULL, created_at TEXT NOT NULL, consent_version TEXT NOT NULL,
        consent_text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'waiting')''')
    try:
        with db:yield db
    finally:db.close()

def register(root,data):
    if not isinstance(data,dict) or data.get('consent') is not True or data.get('consentVersion')!=CONSENT_VERSION:raise ValueError('กรุณาอ่านและติ๊กความยินยอมก่อนลงทะเบียน')
    names=[data.get(k) for k in ('firstName','lastName')]
    if any(not isinstance(n,str) or not 1<=len(n.strip())<=80 for n in names):raise ValueError('กรุณากรอกชื่อและนามสกุล')
    phone=re.sub(r'[\s()-]','',data.get('phone',''))
    if phone.startswith('+66'):phone='0'+phone[3:]
    if not re.fullmatch(r'0[0-9]{8,9}',phone):raise ValueError('กรุณากรอกเบอร์โทรไทย 9–10 หลัก')
    request_id=data.get('requestId','')
    try:uuid.UUID(request_id)
    except Exception:raise ValueError('รหัสคำขอไม่ถูกต้อง กรุณารีเฟรชหน้า')
    with connect(root) as db:
        db.execute('INSERT OR IGNORE INTO registrations (id,request_id,first_name,last_name,phone,created_at,consent_version,consent_text) VALUES (?,?,?,?,?,?,?,?)',
                   (str(uuid.uuid4()),request_id,names[0].strip(),names[1].strip(),phone,datetime.now(timezone.utc).isoformat(),CONSENT_VERSION,CONSENT_TEXT))
        row=db.execute('SELECT queue,id FROM registrations WHERE request_id=?',(request_id,)).fetchone()
    return dict(saved=True,queue=row['queue'],code=row['id'])

def session_id(handler):
    try:return SimpleCookie(handler.headers.get('Cookie','')).get('stomp_admin').value
    except Exception:return ''
def admin(handler):
    sid=session_id(handler)
    with SESSION_LOCK:
        expiry=SESSIONS.get(sid,0)
        if expiry<time.time():SESSIONS.pop(sid,None);return False
        return bool(sid)
def session_cookie(token,max_age):
    secure='; Secure' if os.environ.get('STOMP_PUBLIC_URL','').startswith('https://') else ''
    return f'stomp_admin={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={max_age}'+secure

def get(handler):
    path=urlsplit(handler.path).path
    if path=='/api/admin-session':handler.reply(200 if admin(handler) else 401,{'authenticated':admin(handler)});return True
    if path=='/api/registration-info':handler.reply(200,dict(url=handler.server.registration_url,consentText=CONSENT_TEXT,consentVersion=CONSENT_VERSION));return True
    if path=='/api/registration-qr.svg':
        import qrcode
        from qrcode.image.svg import SvgPathImage
        output=io.BytesIO();qrcode.make(handler.server.registration_url,image_factory=SvgPathImage,box_size=8,border=4).save(output)
        body=output.getvalue();handler.send_response(200);handler.send_header('Content-Type','image/svg+xml');handler.send_header('Content-Length',str(len(body)));handler.end_headers();handler.wfile.write(body);return True
    if path=='/api/registrations':
        if not admin(handler):handler.reply(401,{'error':'กรุณาเข้าสู่ระบบ'});return True
        from urllib.parse import parse_qs
        query=parse_qs(urlsplit(handler.path).query)
        try:page=max(1,int(query.get('page',['1'])[0]))
        except ValueError:page=1
        search=query.get('q',[''])[0][:80]
        with connect(handler.server.root) as db:
            where='WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?';args=tuple('%'+search+'%' for _ in range(3))
            total=db.execute('SELECT COUNT(*) FROM registrations '+where,args).fetchone()[0]
            rows=db.execute('SELECT queue,id,first_name,last_name,phone,created_at,consent_version,status FROM registrations '+where+' ORDER BY queue DESC LIMIT 50 OFFSET ?',(*args,(page-1)*50)).fetchall()
        handler.reply(200,dict(rows=[dict(row) for row in rows],total=total,page=page));return True
    return False

def post(handler):
    path=urlsplit(handler.path).path
    if path=='/api/register':
        try:
            length=int(handler.headers.get('Content-Length','0'))
            if not 0<length<=8192:raise ValueError('Invalid request')
            data=json.loads(handler.rfile.read(length));handler.reply(200,register(handler.server.root,data))
        except (ValueError,json.JSONDecodeError) as e:handler.reply(400,{'error':str(e)})
        return True
    if path in ('/api/admin-login','/api/admin-logout'):
        if path=='/api/admin-logout':
            with SESSION_LOCK:SESSIONS.pop(session_id(handler),None)
            handler.reply(200,{'ok':True},cookie=session_cookie('',0));return True
        try:
            length=int(handler.headers.get('Content-Length','0'));data=json.loads(handler.rfile.read(length))
            user=os.environ.get('STOMP_ADMIN_USER','admin');password=os.environ.get('STOMP_ADMIN_PASSWORD','1234')
            if data.get('username')!=user or not secrets.compare_digest(str(data.get('password','')),password):handler.reply(401,{'error':'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'});return True
            token=secrets.token_urlsafe(32)
            with SESSION_LOCK:SESSIONS[token]=time.time()+SESSION_SECONDS
            handler.reply(200,{'ok':True},cookie=session_cookie(token,SESSION_SECONDS))
        except Exception:handler.reply(400,{'error':'เข้าสู่ระบบไม่สำเร็จ'})
        return True
    return False
