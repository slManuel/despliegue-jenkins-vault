#!/usr/bin/env python3
"""Verify the live LOCAL demo without printing credential or secret values."""
import importlib.util, json, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

spec=importlib.util.spec_from_file_location('demo_setup',Path(__file__).with_name('setup.py'))
demo=importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
def get(kind,name=None):
    args=['-n','development','get',kind]
    if name: args.append(name)
    return json.loads(demo.k('development',*args,'-o','json'))
def http(path):
    with urllib.request.urlopen('http://127.0.0.1:18081'+path,timeout=10) as response:
        return json.load(response)
deployment=get('deployment','devops-java-service')
assert deployment['spec']['replicas']==2 and deployment['status']['readyReplicas']==2
pods=get('pods')['items']
pods=[p for p in pods if p['metadata'].get('labels',{}).get('app')=='devops-java-service' and not p['metadata'].get('deletionTimestamp')]
assert len(pods)==2 and all(all(c['ready'] for c in p['status']['containerStatuses']) for p in pods)
mounts=get('secretproviderclasspodstatuses')['items']
for pod in pods:
    assert any(m['status']['mounted'] and m['status']['podName']==pod['metadata']['name'] for m in mounts)
    demo.k('development','-n','development','exec',pod['metadata']['name'],'--','sh','-c','test -s /app/config/application.properties')
assert http('/health/ready')['status']=='UP'
assert http('/api/secret')['value']=='demostracion-cuscatlan'
config=http('/api/config')
assert config['property']=='configuracion-desde-CSI'
conditions=get('vaultstaticsecret','vault-config')['status']['conditions']
assert all(any(c['type']==kind and c['status']=='True' for c in conditions) for kind in ('Healthy','Ready','SecretSynced'))
# Real JWT auth followed by a policy denial; tokens exist only in process memory.
jwt=demo.k('tools','-n','jenkins','create','token','jenkins-pipeline','--audience=vault','--duration=10m').strip()
login=demo.api('POST','auth/deployment/login',{'role':'jenkins','jwt':jwt})
token=login['auth']['client_token']
try:
    demo.api('GET','kv/data/demo/app',token=token)
    try:
        demo.api('GET','kv/data/demo/config',token=token)
        raise AssertionError('Jenkins policy allowed unrelated CSI configuration')
    except urllib.error.HTTPError as error:
        assert error.code==403
finally:
    demo.api('POST','auth/token/revoke-self',{},token)
wrong=demo.k('tools','-n','jenkins','create','token','default','--audience=vault','--duration=10m').strip()
try:
    demo.api('POST','auth/deployment/login',{'role':'jenkins','jwt':wrong})
    raise AssertionError('Wrong ServiceAccount accepted')
except urllib.error.HTTPError as error:
    assert error.code in (400,403)
result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'environment':'LOCAL kind; no AWS apply','two_ready_replicas':True,'image':deployment['spec']['template']['spec']['containers'][0]['image'],'csi_mounted_both_pods':True,'http_env_matches_demo':True,'http_property_matches_csi':True,'vso_feature':config['feature'],'vso_healthy':True,'jenkins_vault_login':True,'jenkins_unrelated_path_denied':True,'wrong_serviceaccount_denied':True}
output=Path(__file__).with_name('evidence.json')
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
