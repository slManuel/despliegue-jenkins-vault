#!/usr/bin/env python3
"""Start/reuse only the explicitly named LOCAL demo resources. Never deletes."""
import importlib.util, subprocess, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('demo_setup', Path(__file__).with_name('setup.py'))
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

def execute(args):
    subprocess.run(args, check=True)

def exists(name):
    return subprocess.run(['docker', 'inspect', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

# A stopped demo is an explicit operator decision: do not silently resume it.
for container in ('cuscatlan-tools-control-plane','cuscatlan-tools-worker','cuscatlan-tools-worker2','cuscatlan-development-control-plane','cuscatlan-development-worker','cuscatlan-registry','cuscatlan-git'):
    if exists(container) and demo.run(['docker','inspect',container,'--format','{{.State.Running}}']).strip()!='true':
        raise SystemExit('Demo resources are stopped. Reactivation requires an explicit operator action; no images or services were started.')

execute(['docker', 'build', '-t', 'local/jenkins-controller:validation', str(demo.ROOT/'images/jenkins')])
execute(['docker', 'build', '--build-arg', 'KUBECTL_VERSION=v1.34.0', '-t', 'local/jenkins-agent:kind', str(demo.ROOT/'images/agent')])
clusters = demo.run(['kind', 'get', 'clusters']).splitlines()
for short in ('tools', 'development'):
    name = 'cuscatlan-'+short
    config = demo.STATE/(short+'.kubeconfig')
    if name not in clusters:
        execute(['kind', 'create', 'cluster', '--config', str(demo.ROOT/'local-demo'/(short+'-kind.yaml')), '--kubeconfig', str(config)])
    elif not config.exists():
        demo.save(config, demo.run(['kind', 'get', 'kubeconfig', '--name', name]))
    config.chmod(0o600)

limits = {'cuscatlan-tools-control-plane':('1g','2g','1.5'), 'cuscatlan-tools-worker':('4g','5g','3'), 'cuscatlan-tools-worker2':('1g','2g','1'), 'cuscatlan-development-control-plane':('1g','2g','1.5'), 'cuscatlan-development-worker':('2g','3g','2')}
for node, (memory, swap, cpus) in limits.items():
    execute(['docker','update','--memory',memory,'--memory-swap',swap,'--cpus',cpus,node])
for image in ('local/jenkins-controller:validation', 'local/jenkins-agent:kind'):
    execute(['kind','load','docker-image',image,'--name','cuscatlan-tools','--nodes','cuscatlan-tools-worker'])

scm = demo.STATE/'scm'
scm.mkdir(exist_ok=True)
bare = scm/'devops-java-service.git'
if not bare.exists():
    execute(['git','clone','--bare',str(demo.APP),str(bare)])
else:
    execute(['git','--git-dir='+str(bare),'fetch',str(demo.APP),'main:main'])
execute(['git','--git-dir='+str(bare),'update-server-info'])
if not exists('cuscatlan-registry'):
    execute(['docker','run','-d','--name','cuscatlan-registry','--network','kind','--restart','unless-stopped','--memory','128m','--cpus','.3','-p','127.0.0.1:15000:5000','-v','cuscatlan-registry-data:/var/lib/registry','registry:2'])
if not exists('cuscatlan-git'):
    execute(['docker','run','-d','--name','cuscatlan-git','--network','kind','--restart','unless-stopped','--read-only','--memory','96m','--cpus','.3','-p','127.0.0.1:18082:8000','-v',str(scm)+':/srv:ro','-w','/srv','python:3.11-slim','python','-m','http.server','8000'])
demo.prepare()
demo.configure_vault()
demo.operators()
demo.jenkins()
print('LOCAL resources ready. Validate and trigger the real Jenkins job using jenkins-api.py.')
