"""Single-school local pilot authentication. Sessions expire after 8 hours."""
import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie
from server import connect

def init():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS accounts(username TEXT PRIMARY KEY,salt TEXT,password TEXT,role TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,username TEXT,expires REAL)')

def digest(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000).hex()

def add(username,password,role):
    init()
    if role not in ('teacher','student') or len(password)<8 or not username.strip():raise ValueError('账号不能为空，密码至少8位')
    salt=secrets.token_hex(16)
    with connect() as c:c.execute('INSERT INTO accounts VALUES(?,?,?,?)',(username,salt,digest(password,salt),role))

def count():
    init()
    with connect() as c:return c.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]

def login(username,password):
    init()
    with connect() as c:
        row=c.execute('SELECT salt,password,role FROM accounts WHERE username=?',(username,)).fetchone()
        if not row or not hmac.compare_digest(row[1],digest(password,row[0])):raise ValueError('账号或密码错误')
        token=secrets.token_urlsafe(32)
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,username,time.time()+28800))
        return token,dict(username=username,role=row[2])

def user(cookie):
    init(); cookies=SimpleCookie()
    try:cookies.load(cookie or '');token=cookies['teaching_session'].value
    except (KeyError,ValueError):return None
    with connect() as c:
        r=c.execute('SELECT a.username,a.role FROM sessions s JOIN accounts a ON a.username=s.username WHERE s.token=? AND s.expires>?',(token,time.time())).fetchone()
    return dict(username=r[0],role=r[1]) if r else None

def logout(cookie):
    cookies=SimpleCookie();cookies.load(cookie or '')
    if 'teaching_session' in cookies:
        with connect() as c:c.execute('DELETE FROM sessions WHERE token=?',(cookies['teaching_session'].value,))
