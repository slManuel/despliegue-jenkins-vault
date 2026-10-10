#!/usr/bin/env python3
"""Interact with localhost Jenkins without putting its password in argv or logs."""
import base64,http.cookiejar,json,sys,urllib.parse,urllib.request
from pathlib import Path
state=Path.home()/'.local/state/cuscatlan-demo'
auth=base64.b64encode(b'local-devops:'+(state/'jenkins-admin.password').read_bytes()).decode()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(path,data=None,headers=None):
 h={'Authorization':'Basic '+auth};h.update(headers or {})
 return opener.open(urllib.request.Request('http://127.0.0.1:18080'+path,data=data,headers=h),timeout=30)
cmd=sys.argv[1]
if cmd=='trigger':
 crumb=json.load(call('/crumbIssuer/api/json'))
 fail=len(sys.argv)>2 and sys.argv[2]=='fail'
 path='/job/cuscatlan-local/buildWithParameters'
 with call(path,b'FAIL_ROLLOUT=true' if fail else b'FAIL_ROLLOUT=false',{crumb['crumbRequestField']:crumb['crumb'],'Content-Type':'application/x-www-form-urlencoded'}) as r: print('Build queued:',r.status,r.headers.get('Location',''))
elif cmd=='status':
 d=json.load(call('/job/cuscatlan-local/api/json?tree=builds[number,result,building,url],lastBuild[number,result,building],queueItem[id]'))
 print(json.dumps(d,indent=2))
elif cmd=='log':
 data=call('/job/cuscatlan-local/'+sys.argv[2]+'/consoleText').read().decode()
 # Never include the administrative password, even if a misconfigured plugin echoed it.
 data=data.replace((state/'jenkins-admin.password').read_text(),'[REDACTED]')
 print(data)
elif cmd=='stages':
 print(call('/job/cuscatlan-local/'+sys.argv[2]+'/wfapi/describe').read().decode())

elif cmd=='validate':
 crumb=json.load(call('/crumbIssuer/api/json'))
 app=Path(__file__).resolve().parents[2]/'devops-java-service'
 file=app/(sys.argv[2] if len(sys.argv)>2 else 'local-demo/Jenkinsfile')
 data=urllib.parse.urlencode({'jenkinsfile':file.read_text()}).encode()
 print(call('/pipeline-model-converter/validate',data,{crumb['crumbRequestField']:crumb['crumb'],'Content-Type':'application/x-www-form-urlencoded'}).read().decode())
