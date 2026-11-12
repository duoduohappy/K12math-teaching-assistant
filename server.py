import csv
import io
import json
import random
import sqlite3
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / 'classroom.sqlite3'
TOPICS = {'移项': '等式两边同时加减同一个数，等式仍然成立。移项时注意符号变化。', '去括号': '括号前是负号时，去括号后括号内各项都要变号。', '去分母': '等式两边每一项同时乘以分母的公倍数，注意不能漏乘。'}

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect():
    c = sqlite3.connect(DB, factory=ClosingConnection)
    c.execute('CREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY, kind TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
    return c

def save(kind, data):
    with connect() as c:
        c.execute('INSERT INTO artifacts(kind,content) VALUES (?,?)', (kind, json.dumps(data, ensure_ascii=False)))

def generate(topic, count):
    if topic not in TOPICS:
        raise ValueError('请选择已支持的知识点')
    count = max(1, min(20, int(count)))
    questions = []
    for i in range(count):
        a, b, x = random.randint(2, 9), random.randint(1, 9), random.randint(-8, 8)
        if topic == '移项':
            text, rhs, solution = f'{a}x + {b} = {a*x+b}', a*x+b, f'两边减去 {b}，得到 {a}x = {a*x}；再除以 {a}。'
            lhs = a*x+b
        elif topic == '去括号':
            text, rhs, solution = f'{a}(x + {b}) = {a*(x+b)}', a*(x+b), f'展开得 {a}x + {a*b} = {a*(x+b)}，再移项、系数化为 1。'
            lhs = a*(x+b)
        else:
            text, rhs, solution = f'(x + {b}) / {a} = {Fraction(x+b,a)}', Fraction(x+b,a), f'两边同乘 {a}，得 x + {b} = {x+b}，再两边减去 {b}。'
            lhs = Fraction(x+b,a)
        questions.append(dict(id=f'Q{i+1}', topic=topic, text=text, answer=str(x), explanation=solution, verified=lhs==rhs))
    return questions

def assess(rows, questions):
    bank = {q['id']: q for q in questions}
    totals, details, seen = {}, [], set()
    for row in rows:
        student, qid = row.get('student','').strip(), row.get('question_id','').strip()
        if not student or qid not in bank:
            raise ValueError('每行须有 student 和有效的 question_id')
        if (student,qid) in seen:
            raise ValueError(f'重复提交：{student}/{qid}')
        seen.add((student,qid))
        q = bank[qid]
        try:
            correct = Fraction(row.get('answer','').strip()) == Fraction(q['answer'])
        except (ValueError, ZeroDivisionError):
            raise ValueError(f'{student}/{qid} 的答案须为整数、小数或分数')
        t = totals.setdefault(q['topic'], {'correct':0,'total':0})
        t['total'] += 1
        t['correct'] += int(correct)
        details.append(dict(student=student, question_id=qid, correct=correct))
    if not details:
        raise ValueError('没有答题记录')
    summary = [dict(topic=k, **v, rate=round(v['correct']/v['total']*100,1), suggestion='安排基础巩固与教师追问，收集解题过程后确认错因。' if v['correct']/v['total'] < .8 else '可安排迁移练习，继续观察。') for k,v in totals.items()]
    return dict(students=len({d['student'] for d in details}), submissions=len(details), summary=summary, details=details, note='统计仅覆盖已导入答案；未提交不计为错误。最终答案不能直接证明具体错因。')

class Handler(BaseHTTPRequestHandler):
    def current_user(self):
        from access import user
        return user(self.headers.get('Cookie'))

    def do_GET(self):
        if self.path=='/health':
            self.respond(200,{'status':'ok'});return
        if self.path=='/access.js':
            self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.end_headers();self.wfile.write((ROOT/'access.js').read_bytes());return
        if self.path=='/api/account':
            from access import count
            self.respond(200,dict(user=self.current_user(),setup_required=count()==0));return
        if self.path.startswith('/api/'):
            u=self.current_user()
            if not u:self.respond(401,{'error':'请先登录'});return
            if u['role']=='student' and not self.path.startswith('/api/student/'):
                self.respond(403,{'error':'学生不可访问教师数据'});return
            if u['role']=='student' and self.path.startswith('/api/student/'):
                from workflow import get
                try:
                    a=get(self.path.rsplit('/',1)[-1]);cl=get(a['class_id'])
                    if u['username'] not in a.get('target_students',cl['students']):self.respond(403,{'error':'任务未指派给你'});return
                except (ValueError,KeyError):self.respond(404,{'error':'任务不存在'});return
        if self.path == '/lesson_workspace.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'lesson_workspace.js').read_bytes()); return
        if self.path == '/grades.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'grades.js').read_bytes()); return
        if self.path == '/closedloop.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'closedloop.js').read_bytes()); return
        if self.path == '/agent.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'agent.js').read_bytes()); return
        if self.path == '/product.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'product.js').read_bytes()); return
        if self.path == '/demo.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'demo.js').read_bytes()); return
        if self.path.split('?')[0] == '/workflow':
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'workflow.html').read_bytes()); return
        if self.path == '/interview.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'interview.js').read_bytes()); return
        if self.path == '/visual.js':
            self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'visual.js').read_bytes()); return
        if self.path == '/api/workflow':
            from workflow import listing
            self.respond(200, listing()); return
        if self.path.startswith('/api/student/'):
            from workflow import get
            try:
                a=get(self.path.rsplit('/',1)[-1]); self.respond(200,dict(id=a['id'],purpose=a['purpose'],questions=[{k:q[k] for k in ['id','text','topic']} for q in a['questions']]))
            except (ValueError,KeyError): self.respond(404,{'error':'课堂或作业不存在'})
            return
        if self.path == '/api/history':
            with connect() as c:
                items = [dict(id=r[0],kind=r[1],content=json.loads(r[2]),created=r[3]) for r in c.execute('SELECT id,kind,content,created FROM artifacts ORDER BY id DESC LIMIT 20')]
            self.respond(200, items)
        elif self.path == '/':
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write((ROOT/'index.html').read_bytes())
        else:
            self.respond(404, {'error':'不存在'})

    def respond(self, status, data):
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.end_headers(); self.wfile.write(json.dumps(data,ensure_ascii=False).encode())

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length',0))
            if size > 1000000: raise ValueError('输入过大')
            d = json.loads(self.rfile.read(size))
            if self.path.startswith('/api/account/'):
                import access
                route=self.path.rsplit('/',1)[-1]
                if route=='setup':
                    # Serialize setup to prevent two first teachers being created concurrently.
                    with SETUP_LOCK:
                        if access.count():self.respond(403,{'error':'系统已经初始化'});return
                        access.add(d['username'],d['password'],'teacher')
                    self.respond(200,{'ok':True});return
                if route=='login':
                    token,u=access.login(d['username'],d['password']);self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Set-Cookie',f'teaching_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800');self.end_headers();self.wfile.write(json.dumps(u).encode());return
                if route=='logout':access.logout(self.headers.get('Cookie'));self.respond(200,{'ok':True});return
                u=self.current_user()
                if not u or u['role']!='teacher':self.respond(403,{'error':'仅教师可管理账号'});return
                if route=='create':
                    access.add(d['username'],d['password'],'student');self.respond(200,{'ok':True});return
                raise ValueError('未知账号操作')
            u=self.current_user()
            if not u:self.respond(401,{'error':'请先登录'});return
            if u['role']=='student':
                if self.path!='/api/workflow/submit':self.respond(403,{'error':'仅教师可执行该操作'});return
                d['student']=u['username']
            if self.path == '/api/education-agent':
                from education_agent import run
                self.respond(200,run(d)); return
            if self.path.startswith('/api/interview/'):
                from interview import action
                self.respond(200,action(self.path.rsplit('/',1)[-1],d)); return
            if self.path.startswith('/api/workflow/'):
                from workflow import action
                self.respond(200,action(self.path.rsplit('/',1)[-1],d)); return
            if self.path == '/api/plan':
                topic = d['topic']
                if topic not in TOPICS: raise ValueError('未知知识点')
                minutes = int(d.get('minutes',40))
                if not 20 <= minutes <= 120: raise ValueError('课时须为20—120分钟')
                source = d.get('source','').strip()[:12000]
                data = dict(title=f'七年级数学 · {topic}', source=source or f'自编演示知识卡 / {topic}：{TOPICS[topic]}', provenance='教师提供资料（待审核）' if source else '自编演示材料，非特定教材原文', objectives=[f'理解{topic}对应的等式变形规则','独立完成变形并代入检验'], boundary='只使用一元一次方程与等式性质；不引入后续学段方法。', sections=[dict(title=t, minutes=m) for t,m in zip(['复习等式性质','例题讲解与追问','学生独立练习','随堂检测与反馈'],[minutes//5,minutes//3,minutes//3,minutes-minutes//5-2*(minutes//3)])], focus=TOPICS[topic], class_context=d.get('context','基础混合班'), review='待教师审核', mode='规则模板生成；未接入大模型，不宣称教材检索或课标对齐。')
            elif self.path == '/api/questions':
                data = generate(d['topic'],d.get('count',5))
            elif self.path == '/api/assess':
                data = assess(list(csv.DictReader(io.StringIO(d['csv'].lstrip('\ufeff')))),d['questions'])
            elif self.path == '/api/save':
                data = d['content']
            else:
                self.respond(404, {'error':'不存在'}); return
            save(self.path.split('/')[-1],data)
            self.respond(200,data)
        except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e:
            self.respond(400,{'error':str(e)})

import threading
SETUP_LOCK=threading.Lock()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('TEACHING_PORT', '18769'))
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Listening: http://127.0.0.1:{port}/workflow', flush=True)
    httpd.serve_forever()
