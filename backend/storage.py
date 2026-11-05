"""Private local storage or server-only Supabase Storage."""
import hashlib
from pathlib import Path
from urllib.parse import quote
import httpx

class Storage:
    def __init__(self, config):
        self.mode = config.get('STORAGE_MODE', 'local')
        self.root = Path(config['DATA_DIR']).resolve() / 'objects'
        self.root.mkdir(parents=True, exist_ok=True)
        self.url = config.get('SUPABASE_URL', '').rstrip('/')
        self.key = config.get('SUPABASE_SERVICE_ROLE_KEY', '')
        self.bucket = config.get('STORAGE_BUCKET', 'traffic-private')
        self.max_bytes = int(config.get('MAX_UPLOAD_BYTES', 100 * 1024 * 1024))
        self.max_local_bytes=int(config.get('MAX_LOCAL_STORAGE_BYTES',5*1024*1024*1024))
    def capacity(self, additional=0):
        if self.mode=='local' and sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())+additional>self.max_local_bytes:
            raise ValueError('Local storage quota reached; run retention or increase the configured quota')
    def path(self, key):
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root): raise ValueError('Invalid object key')
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    def headers(self): return {'Authorization': f'Bearer {self.key}', 'apikey': self.key}
    def endpoint(self, key): return f'{self.url}/storage/v1/object/{self.bucket}/{quote(key, safe="/")}'
    def put(self, key, data, content_type='image/jpeg'):
        if len(data) > self.max_bytes: raise ValueError('Object exceeds limit')
        if self.mode == 'local': self.capacity(len(data)); self.path(key).write_bytes(data)
        else:
            with httpx.Client(timeout=45) as client:
                r = client.post(self.endpoint(key), headers={**self.headers(), 'Content-Type': content_type, 'x-upsert':'true'}, content=data)
                r.raise_for_status()
        return {'key':key, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes':len(data), 'content_type':content_type}
    def get(self, key):
        if self.mode == 'local': return self.path(key).read_bytes()
        with httpx.Client(timeout=45) as client:
            r = client.get(self.endpoint(key), headers=self.headers())
            r.raise_for_status()
            if len(r.content) > self.max_bytes: raise ValueError('Object exceeds limit')
            return r.content
    def materialize(self, key, path):
        if self.mode == 'local':
            source = self.path(key)
            if source.stat().st_size > self.max_bytes: raise ValueError('Upload exceeds limit')
            return source
        with httpx.Client(timeout=60) as client:
            with client.stream('GET', self.endpoint(key), headers=self.headers()) as r:
                r.raise_for_status()
                total = 0
                with open(path, 'wb') as f:
                    for chunk in r.iter_bytes(1024*1024):
                        total += len(chunk)
                        if total > self.max_bytes: raise ValueError('Upload exceeds limit')
                        f.write(chunk)
        return Path(path)
    def delete(self, key):
        if self.mode == 'local': self.path(key).unlink(missing_ok=True)
        else:
            with httpx.Client(timeout=20) as client: client.delete(self.endpoint(key), headers=self.headers()).raise_for_status()
    def signed_upload(self, key):
        with httpx.Client(timeout=20) as client:
            r = client.post(f'{self.url}/storage/v1/object/upload/sign/{self.bucket}/{quote(key, safe="/")}', headers=self.headers(), json={})
            r.raise_for_status()
            value = r.json()
            return f'{self.url}/storage/v1{value.get("url") or value.get("signedURL")}'
    def signed_download(self, key):
        with httpx.Client(timeout=20) as client:
            r=client.post(f'{self.url}/storage/v1/object/sign/{self.bucket}/{quote(key,safe="/")}',headers=self.headers(),json={'expiresIn':60})
            r.raise_for_status()
            return self.url+'/storage/v1'+r.json()['signedURL']
