"""Local fault injection proxy: simulate a real dropped network connection for WebKit."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import httpx,json,os
class Handler(BaseHTTPRequestHandler):
    def forward(self):
        if Path('/tmp/focus3-test-network-down').exists():
            self.connection.shutdown(2);self.connection.close();return
        body=self.rfile.read(int(self.headers.get('Content-Length','0')))
        headers={k:v for k,v in self.headers.items() if k.lower() not in ['host','connection','content-length','accept-encoding']}
        with httpx.Client(timeout=30) as client:
            r=client.request(self.command,'http://127.0.0.1:8005'+self.path,content=body,headers=headers)
        content=r.content
        flag=os.getenv('FOCUS_TEST_INVALID_QUEUE_TIME_FLAG','')
        if self.command=='GET' and self.path=='/api/focus-calendar/diagnostics' and r.status_code==200 and flag and Path(flag).exists():
            payload=r.json();payload['agent_jobs'].update(queued=1,oldest_queued_age_seconds=None)
            content=json.dumps(payload).encode()
        self.send_response(r.status_code)
        for k,v in r.headers.multi_items():
            if k.lower() not in ['connection','transfer-encoding','content-encoding','content-length']:self.send_header(k,v)
        self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    do_GET=forward;do_POST=forward;do_PUT=forward;do_PATCH=forward;do_HEAD=forward
    def log_message(self,*_):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8006),Handler).serve_forever()
