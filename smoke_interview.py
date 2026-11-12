"""Exercises real local HTTP endpoints against an isolated temporary database."""
import json
import tempfile
import threading
import urllib.request
from pathlib import Path
import server

def main():
    old=server.DB
    with tempfile.TemporaryDirectory() as tmp:
        server.DB=Path(tmp)/'smoke.sqlite3'
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{httpd.server_port}'
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def post(path,data):
            req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
            with op.open(req,timeout=10) as r:return json.load(r)
        try:
            for path in ['/workflow','/interview.js']:
                with op.open(base+path) as r:assert r.status==200
            post('/api/workflow/demo',{})
            with op.open(base+'/api/workflow') as r: records=json.load(r)
            m=next(x for x in records if x['kind']=='material'); c=next(x for x in records if x['kind']=='class')
            d=post('/api/interview/lesson',dict(material=m['id'],topic='移项',mode='preset'))
            assert d['references'] and len(d['questions'])==3
            l=post('/api/workflow/lesson',dict(material=m['id'],class_id=c['id'],text=d['text']))
            a=post('/api/workflow/publish',dict(lesson=l['id'],topic='移项',count=3))
            post('/api/workflow/submit',dict(assignment=a['id'],student='S01',answers={q['id']:str(int(q['answer'])+1) for q in a['questions']}))
            r=post('/api/workflow/report',dict(assignment=a['id']))
            assert len(r['missing'])==11
            remedial=post('/api/interview/remedial',dict(assignment=a['id'],student='S01'))
            assert len(remedial['practice'])==3
            assert post('/api/interview/verify',dict(equation='3x+5=17',answer='4'))['correct']
            print('PASS: real HTTP material -> grounded draft -> approved lesson -> assignment -> submission -> report -> remedial; static UI and JS return 200')
        finally:
            httpd.shutdown();httpd.server_close();server.DB=old

if __name__=='__main__':main()
