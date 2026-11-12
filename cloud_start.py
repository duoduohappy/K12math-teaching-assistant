"""Resettable demonstration deployment, never uses the local account database."""
import os
from http.server import ThreadingHTTPServer
import server
import access
from workflow import action

if __name__=='__main__':
    password=os.environ.get('DEMO_TEACHER_PASSWORD','')
    if len(password)<12:raise SystemExit('Set DEMO_TEACHER_PASSWORD with at least 12 characters in Render environment settings.')
    if access.count()==0:access.add('teacher',password,'teacher')
    action('demo',{})
    port=int(os.environ.get('PORT','10000'))
    print(f'Demo server listening on port {port}',flush=True)
    ThreadingHTTPServer((os.environ.get('HOST','0.0.0.0'),port),server.Handler).serve_forever()
