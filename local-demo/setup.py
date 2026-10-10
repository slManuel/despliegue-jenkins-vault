#!/usr/bin/env python3
"""LOCAL ONLY. No AWS calls. Runtime secrets stay outside Git in 0700 state dir."""
import base64,json,os,secrets,ssl,subprocess,time,urllib.request,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT.parent/'devops-java-service'
STATE=Path.home()/'.local/state/cuscatlan-demo'
STATE.mkdir(parents=True,exist_ok=True);STATE.chmod(0o700)
def run(args, data=None, quiet=True):
 p=subprocess.run(args,input=data,text=True,capture_output=True)
 if p.returncode:raise RuntimeError('Command failed: '+args[0]+' '+p.stderr[-2500:])
 if not quiet:print(p.stdout.strip(),flush=True)
 return p.stdout

def k(cluster,*args,data=None,quiet=True):
 return run(['docker','run','--rm','-i','--network','host','--user','1000:1000','-v',f'{STATE}:{STATE}:ro','-v',f'{ROOT}:{ROOT}:ro','-e',f'KUBECONFIG={STATE/(cluster+".kubeconfig")}','--entrypoint','kubectl','local/jenkins-agent:kind',*args],data,quiet)

def apply(cluster,docs):
 k(cluster,'apply','-f','-',data=yaml.safe_dump_all(docs,sort_keys=False),quiet=False)

def secret(cluster,namespace,name,files,kind='Secret',typ=None):
 d={'apiVersion':'v1','kind':kind,'metadata':{'name':name,'namespace':namespace},'data':{n:base64.b64encode(v).decode() if kind=='Secret' else v.decode() for n,v in files.items()}}
 if typ:d['type']=typ
 apply(cluster,[d])

def ip(name):return run(['docker','inspect',name,'--format','{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}']).strip()

def save(path,data):
 path.write_text(data);path.chmod(0o600)

def manifests(path):return [x for x in yaml.safe_load_all(path.read_text()) if x]

def prepare():
 for cluster in ('tools','development'):
  p=STATE/(cluster+'.kubeconfig');c=yaml.safe_load(p.read_text());c['contexts'][0]['name']=cluster;c['current-context']=cluster;save(p,yaml.safe_dump(c))
 apply('tools',manifests(ROOT/'k8s/namespaces.yaml'))
 apply('tools',manifests(ROOT/'k8s/rbac.yaml'))
 apply('development',manifests(APP/'k8s/namespace.yaml')+manifests(APP/'k8s/identity.yaml'))
 apply('development',[{'apiVersion':'v1','kind':'Namespace','metadata':{'name':'csi'}}])
 tls=STATE/'tls';tls.mkdir(exist_ok=True)
 if not (tls/'ca.key').exists():
  run(['openssl','req','-x509','-newkey','rsa:3072','-nodes','-days','365','-subj','/CN=LOCAL assessment Vault CA','-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign','-keyout',str(tls/'ca.key'),'-out',str(tls/'ca.crt')])
  run(['openssl','req','-newkey','rsa:3072','-nodes','-subj','/CN=vault.vault.svc.cluster.local','-keyout',str(tls/'tls.key'),'-out',str(tls/'tls.csr')])
  (tls/'extensions.cnf').write_text('subjectAltName=DNS:vault.vault.svc.cluster.local,DNS:vault.vault.svc,DNS:vault,DNS:localhost\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\nkeyUsage=critical,digitalSignature,keyEncipherment\n')
  run(['openssl','x509','-req','-in',str(tls/'tls.csr'),'-CA',str(tls/'ca.crt'),'-CAkey',str(tls/'ca.key'),'-CAcreateserial','-days','90','-extfile',str(tls/'extensions.cnf'),'-out',str(tls/'tls.crt')])
  for p in tls.iterdir():p.chmod(0o600)
 ca=(tls/'ca.crt').read_bytes()
 secret('tools','vault','vault-tls',{n:(tls/n).read_bytes() for n in ('tls.crt','tls.key','ca.crt')})
 secret('tools','jenkins','vault-ca',{'ca.crt':ca},'ConfigMap')
 secret('development','development','vault-ca',{'ca.crt':ca})
 secret('development','csi','vault-ca',{'ca.crt':ca},'ConfigMap')
 pvcs=[d for d in manifests(ROOT/'k8s/storage.yaml') if d['kind']=='PersistentVolumeClaim']
 for p in pvcs:p['spec']['storageClassName']='standard';p['spec']['resources']['requests']['storage']='2Gi'
 apply('tools',pvcs)
 docs=manifests(ROOT/'k8s/vault.yaml')
 for d in docs:
  if d['kind']=='StatefulSet':d['spec']['template']['spec']['containers'][0]['imagePullPolicy']='IfNotPresent'
  if d['kind']=='Service' and d['metadata']['name']=='vault-private':
   d['metadata'].pop('annotations',None);d['spec'].pop('loadBalancerSourceRanges',None);d['spec']['type']='NodePort';d['spec']['publishNotReadyAddresses']=True;d['spec']['ports'][0]['nodePort']=30200
 apply('tools',docs)
 k('tools','-n','vault','wait','--for=jsonpath={.status.phase}=Running','pod/vault-0','--timeout=180s',quiet=False)
 print('LOCAL Vault pod running; init/unseal via TLS next.',flush=True)

CTX=None
ROOT_TOKEN=None
def api(method,path,payload=None,token=None):
 global CTX
 if CTX is None:CTX=ssl.create_default_context(cafile=str(STATE/'tls/ca.crt'))
 headers={'Content-Type':'application/json'}
 if token:headers['X-Vault-Token']=token
 req=urllib.request.Request('https://localhost:18200/v1/'+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers,method=method)
 with urllib.request.urlopen(req,context=CTX,timeout=15) as r:
  data=r.read();return json.loads(data) if data else {}

def configure_vault():
 global ROOT_TOKEN
 for _ in range(30):
  try:status=api('GET','sys/init');break
  except Exception:time.sleep(2)
 else:raise RuntimeError('Vault TLS endpoint not reachable')
 initfile=STATE/'vault-init.json'
 if not status['initialized']:save(initfile,json.dumps(api('POST','sys/init',{'secret_shares':1,'secret_threshold':1})))
 info=json.loads(initfile.read_text());ROOT_TOKEN=info['root_token']
 api('POST','sys/unseal',{'key':info['keys_base64'][0]})
 mounts=api('GET','sys/mounts',token=ROOT_TOKEN)
 mounts=mounts.get('data',mounts)
 if 'kv/' not in mounts:api('POST','sys/mounts/kv',{'type':'kv','options':{'version':'2'}},ROOT_TOKEN)
 for name in ('jenkins','microservicio'):
  api('PUT','sys/policies/acl/'+name,{'policy':(ROOT/'vault'/f'{name}-policy.hcl').read_text()},ROOT_TOKEN)
 auth=api('GET','sys/auth',token=ROOT_TOKEN)
 auth=auth.get('data',auth)
 for mount,cluster,role,subject,policy in [('deployment','tools','jenkins','system:serviceaccount:jenkins:jenkins-pipeline','jenkins'),('development','development','microservicio','system:serviceaccount:development:microservicio','microservicio')]:
  if mount+'/' not in auth:api('POST','sys/auth/'+mount,{'type':'jwt'},ROOT_TOKEN)
  node='cuscatlan-'+cluster+'-control-plane'
  pub=run(['docker','exec',node,'cat','/etc/kubernetes/pki/sa.pub'])
  conf=yaml.safe_load(run(['docker','exec',node,'cat','/etc/kubernetes/manifests/kube-apiserver.yaml']))
  issuer=next(s.split('=',1)[1] for s in conf['spec']['containers'][0]['command'] if s.startswith('--service-account-issuer='))
  api('POST',f'auth/{mount}/config',{'jwt_validation_pubkeys':[pub],'bound_issuer':issuer},ROOT_TOKEN)
  api('POST',f'auth/{mount}/role/{role}',{'role_type':'jwt','user_claim':'sub','bound_subject':subject,'bound_audiences':['vault'],'token_policies':[policy],'token_ttl':'5m','token_max_ttl':'5m'},ROOT_TOKEN)
 api('POST','kv/data/demo/app',{'data':{'DEMO_MESSAGE':'demostracion-cuscatlan','FEATURE_FLAG':'enabled'}},ROOT_TOKEN)
 api('POST','kv/data/demo/config',{'data':{'property':'demo.property=configuracion-desde-CSI'}},ROOT_TOKEN)
 k('tools','-n','vault','rollout','status','statefulset/vault','--timeout=120s',quiet=False)
 print('Vault initialized/unsealed with TLS; separate JWT public keys, policies and demo KV configured. Values omitted.',flush=True)

def operators():
 for name in ('secrets-store-csi','vault-csi','vso'):
  rendered=run(['kubectl','kustomize',str(ROOT/'operators'/name)])
  k('development','apply','--server-side','-f','-',data=rendered,quiet=False)
 k('development','wait','--for=condition=Established','crd/vaultconnections.secrets.hashicorp.com','crd/vaultauths.secrets.hashicorp.com','crd/vaultstaticsecrets.secrets.hashicorp.com','crd/secretproviderclasses.secrets-store.csi.x-k8s.io','--timeout=120s',quiet=False)
 endpoint='https://'+ip('cuscatlan-tools-control-plane')+':30200'
 vault=(APP/'k8s/vault.yaml').read_text().replace('https://REPLACE_VAULT_INTERNAL_DNS:8200',endpoint).replace('environments/development/app','demo/app').replace('environments/development/config','demo/config')
 k('development','apply','-f','-',data=vault,quiet=False)
 apply('development',manifests(APP/'local-demo/service.yaml'))
 print('Official VSO and CSI installed; cross-cluster Vault endpoint uses kind node + NodePort and verified TLS SAN.',flush=True)

def jenkins():
 # Docker registry is isolated to the kind bridge and loopback; no real credentials.
 registry=ip('cuscatlan-registry')+':5000'
 for node in ('cuscatlan-development-control-plane','cuscatlan-development-worker'):
  conf='server = "http://'+registry+'"\n[host."http://'+registry+'"]\n  capabilities = ["pull", "resolve"]\n'
  run(['docker','exec','-i',node,'sh','-c','mkdir -p /etc/containerd/certs.d/'+registry+'; cat > /etc/containerd/certs.d/'+registry+'/hosts.toml'],conf)
  config=run(['docker','exec',node,'cat','/etc/containerd/config.toml'])
  section='[plugins."io.containerd.grpc.v1.cri".registry]'
  if section not in config:
   config+='\n'+section+'\n  config_path = "/etc/containerd/certs.d"\n'
   run(['docker','exec','-i',node,'sh','-c','cat > /etc/containerd/config.toml'],config)
  run(['docker','exec',node,'systemctl','restart','containerd'])
 admin=STATE/'jenkins-admin.password'
 if not admin.exists():save(admin,secrets.token_urlsafe(32))
 secret('tools','jenkins','jenkins-admin',{'username':b'local-devops','password':admin.read_bytes()})
 token=k('development','-n','development','create','token','jenkins-deployer','--duration=2h').strip()
 dev=yaml.safe_load((STATE/'development.kubeconfig').read_text());cluster=dev['clusters'][0]['cluster'];cluster['server']='https://'+ip('cuscatlan-development-control-plane')+':6443'
 cred={'apiVersion':'v1','kind':'Config','clusters':[{'name':'development','cluster':cluster}],'users':[{'name':'jenkins-deployer','user':{'token':token}}],'contexts':[{'name':'development','context':{'cluster':'development','user':'jenkins-deployer','namespace':'development'}}],'current-context':'development'}
 save(STATE/'jenkins-development.kubeconfig',yaml.safe_dump(cred));secret('tools','jenkins','jenkins-local-kubeconfig',{'development.kubeconfig':yaml.safe_dump(cred).encode()})
 secret('tools','jenkins','jenkins-local-init',{'local.groovy':(ROOT/'local-demo/init.groovy').read_bytes()},'ConfigMap')
 docs=manifests(ROOT/'local-demo/jenkins-casc.yaml');c=yaml.safe_load(docs[0]['data']['jenkins.yaml']);c['unclassified']['location']['url']='http://127.0.0.1:18080/';c['jenkins']['globalNodeProperties']=[{'envVars':{'env':[{'key':'LOCAL_REGISTRY','value':registry}]}}];docs[0]['data']['jenkins.yaml']=yaml.safe_dump(c,sort_keys=False)
 for d in docs:
  if d['kind']=='Service':d['spec']['type']='NodePort';d['spec']['ports'][0]['nodePort']=30080
 apply('tools',docs)
 d=manifests(ROOT/'k8s/jenkins-statefulset.yaml')[0];pod=d['spec']['template']['spec'];pod.pop('imagePullSecrets',None);ctr=pod['containers'][0];ctr['image']='local/jenkins-controller:validation';ctr['imagePullPolicy']='IfNotPresent';ctr['env']=[e for e in ctr['env'] if e['name'] not in ('JENKINS_PROMOTION_USER','JENKINS_PROMOTION_PASSWORD')];ctr['env'].append({'name':'LOCAL_SCM_URL','value':'http://'+ip('cuscatlan-git')+':8000/devops-java-service.git'})
 ctr['volumeMounts'] += [{'name':'local-init','mountPath':'/usr/share/jenkins/ref/init.groovy.d/local.groovy','subPath':'local.groovy','readOnly':True},{'name':'local-kubeconfig','mountPath':'/run/local','readOnly':True}]
 pod['volumes'] += [{'name':'local-init','configMap':{'name':'jenkins-local-init'}},{'name':'local-kubeconfig','secret':{'secretName':'jenkins-local-kubeconfig','defaultMode':0o440}}]
 apply('tools',[d]);k('tools','-n','jenkins','rollout','status','statefulset/jenkins','--timeout=300s',quiet=False)
 print('Jenkins ready at http://127.0.0.1:18080; user local-devops. Password only in private runtime file.',flush=True)

if __name__=='__main__':
 import sys
 {'prepare':prepare,'vault':configure_vault,'operators':operators,'jenkins':jenkins}[sys.argv[1]]()
