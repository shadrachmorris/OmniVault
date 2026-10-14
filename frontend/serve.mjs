import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'};
http.createServer((req,res)=>{
  const u = new URL(req.url, 'http://localhost:5500');
  if (/^\/(api|auth|health)(\/|$)/.test(u.pathname) || ['/docs','/openapi.json'].includes(u.pathname)) {
    const p = http.request({hostname:'127.0.0.1',port:8000,path:u.pathname+u.search,method:req.method,headers:{...req.headers,host:'localhost:8000'}}, r=>{res.writeHead(r.statusCode||502,r.headers);r.pipe(res);});
    p.on('error',()=>{if(!res.headersSent)res.writeHead(502,{'content-type':'application/json'});res.end(JSON.stringify({detail:'Backend unreachable on localhost:8000'}));});
    req.pipe(p);return;
  }
  let name;try{name=decodeURIComponent(u.pathname);}catch{res.writeHead(400);res.end();return;}
  const f=path.resolve(ROOT,'.'+(name==='/'?'/index.html':name));
  if(!f.startsWith(ROOT+path.sep)){res.writeHead(403);res.end('Forbidden');return;}
  fs.stat(f,(err,stat)=>{if(err||!stat.isFile()){res.writeHead(404);res.end('Not found');return;}
    res.writeHead(200,{'content-type':types[path.extname(f)]||'application/octet-stream','x-content-type-options':'nosniff'});fs.createReadStream(f).pipe(res);});
}).listen(5500,'127.0.0.1',()=>console.log('OmniVault at http://localhost:5500'));
