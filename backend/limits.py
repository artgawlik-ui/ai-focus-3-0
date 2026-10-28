"""Bound API request bodies before JSON/multipart parsing, including chunked requests."""
from starlette.responses import JSONResponse
class BodyLimitMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] in ('GET','HEAD','OPTIONS') or not scope['path'].startswith('/api/'):
            return await self.app(scope,receive,send)
        maximum=6*1024*1024 if scope['path']=='/api/import' else 256*1024
        headers=dict(scope.get('headers',[]))
        try:declared=int(headers.get(b'content-length',b'0'))
        except ValueError:
            return await JSONResponse({'detail':'Nieprawidłowy rozmiar żądania'},status_code=400)(scope,receive,send)
        if declared>maximum:
            return await JSONResponse({'detail':'Żądanie przekracza limit rozmiaru'},status_code=413)(scope,receive,send)
        body=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body.extend(message.get('body',b''))
            if len(body)>maximum:
                return await JSONResponse({'detail':'Żądanie przekracza limit rozmiaru'},status_code=413)(scope,receive,send)
            if not message.get('more_body',False):break
        delivered=False
        async def limited_receive():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':bytes(body),'more_body':False}
            return await receive()
        await self.app(scope,limited_receive,send)
