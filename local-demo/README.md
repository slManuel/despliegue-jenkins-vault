# Demostración real local, sin Helm

**Estado actual: detenida por petición del usuario.** Los siete contenedores están Exited y las direcciones siguientes no responden hasta una reactivación autorizada. Los datos están conservados.

Dos clústeres kind independientes: `cuscatlan-tools` (control plane, worker Jenkins, worker Vault) y `cuscatlan-development` (control plane y worker de aplicación). Kubernetes 1.34.0 fijado por digest; agente kubectl 1.34.0. Los manifiestos cloud siguen preparados para EKS 1.36. Esta demostración prueba la integración; AWS, EBS y NLB requieren la validación cloud posterior.

Jenkins ejecuta un job Pipeline desde Git: checkout → autenticación JWT ante Vault con CA verificada → variable en memoria antes de test/build → Java21 → BuildKit rootless → registro Docker local → Deployment por digest con dos réplicas. VSO sincroniza `FEATURE_FLAG`; CSI monta `application.properties`. No se usa Helm ni se desarrollan operadores alternativos: `operators/` conserva los manifiestos oficiales versionados y sus licencias.

## Acceso y seguimiento

| Servicio | Dirección local |
|---|---|
| Jenkins | http://127.0.0.1:18080/ |
| Job y consolas | http://127.0.0.1:18080/job/cuscatlan-local/ |
| Variable de demostración | http://127.0.0.1:18081/api/secret |
| Propiedad CSI y flag VSO | http://127.0.0.1:18081/api/config |
| Readiness | http://127.0.0.1:18081/health/ready |
| Vault TLS | https://localhost:18200/ |

Jenkins: usuario `local-devops`. Abrir personalmente `~/.local/state/cuscatlan-demo/jenkins-admin.password` para obtener la contraseña; no copiarla en chat, Git o logs. Las herramientas API leen ese archivo directamente y no ponen la contraseña en argumentos. Vault requiere la CA `~/.local/state/cuscatlan-demo/tls/ca.crt`; no se desactiva la verificación TLS. Root token, clave de desellado y kubeconfigs quedan exclusivamente en el directorio privado 0700, con archivos 0600.

## Reproducir en una estación preparada

Requisitos ya disponibles en la estación usada: Docker, kind0.30.0, kubectl (para render Kustomize), Python3 con PyYAML, Git y OpenSSL. `start.py` no instala software en el host ni llama a AWS. El script de bootstrap está validado en sintaxis; no se ha repetido desde cero después de la prueba. Construye imágenes locales, crea/reutiliza exclusivamente los recursos nombrados arriba y conserva los contenedores ajenos. Necesita puertos loopback 18080, 18200, 18081, 15000 y 18082 libres; aproximadamente 10GiB de RAM disponibles y espacio para imágenes.

Para una instalación inicial autorizada (no para reactivar automáticamente los contenedores actualmente detenidos), desde la raíz de este repositorio, con `../devops-java-service` en la misma carpeta:

```sh
python3 local-demo/start.py
python3 local-demo/jenkins-api.py validate
python3 local-demo/jenkins-api.py validate Jenkinsfile
python3 local-demo/jenkins-api.py trigger
python3 local-demo/jenkins-api.py status
# Sustituir N por el número real de ejecución:
python3 local-demo/jenkins-api.py log N
python3 local-demo/verify.py
```

La instalación inicial puede descargar imágenes. El source Git local se sirve en modo lectura y no necesita PAT: es una copia bare del repositorio privado existente en la estación. Los commits de la aplicación deben existir antes de actualizar esa copia:

```sh
git --git-dir="$HOME/.local/state/cuscatlan-demo/scm/devops-java-service.git" fetch ../devops-java-service main:main
git --git-dir="$HOME/.local/state/cuscatlan-demo/scm/devops-java-service.git" update-server-info
```

El kubeconfig del job usa el SA `jenkins-deployer`, limitado al namespace `development`; su token dura dos horas. Para renovarlo, ejecutar `python3 local-demo/setup.py jenkins` y, entre ejecuciones, reiniciar el StatefulSet Jenkins con el contexto privado `tools`. El init Groovy reemplaza la credencial existente al arrancar. La aplicación continúa funcionando durante esa renovación.

## Rollback y rotación

Después de una ejecución correcta, `python3 local-demo/jenkins-api.py trigger fail` usa deliberadamente un tag inexistente sólo en el perfil local. El job debe terminar `FAILURE`, ejecutar `scripts/rollback.sh` antes de limpiar el workspace, restaurar Deployment y secreto previos y recuperar dos réplicas disponibles. Consultar su consola y comprobar los endpoints. Ejecutar posteriormente el job normal para dejar Jenkins en verde.

VSO refresca cada 30s y reinicia el Deployment al cambiar el KV. Cambiar únicamente datos de demostración con un operador autorizado de Vault, comprobar `/api/config` y observar el nuevo rollout. `verify.py` comprueba dos pods listos, CSI montado en ambos, endpoints, reconciliación VSO, login JWT real, denegación de otro path y rechazo de otro ServiceAccount. Guarda únicamente metadatos y resultados en `evidence.json`.

## Límites del perfil local

Los puertos publicados se limitan a 127.0.0.1. El registro HTTP sin autenticación y el servidor Git son exclusivos de la red Docker local; no contienen credenciales reales. El perfil cloud conserva GHCR privado y TLS. NodePort reemplaza los NLB y el provisionador local-path reemplaza EBS sólo para esta prueba. Dos réplicas en un worker no ofrecen tolerancia a la pérdida de ese nodo.

Vault usa Raft persistente de una réplica, desellado manual y una sola clave para la demo; no es una configuración de producción. Tras reiniciar su pod, `python3 local-demo/setup.py vault` lo desella con el archivo privado existente y reconcilia las políticas y datos de demostración. Jenkins no recibe root token. Los mounts JWT usan claves públicas independientes de cada clúster, subject exacto y audience `vault`. El agente usa tokens proyectados de 600s y Vault emite tokens de 5m revocados tras la lectura.

BuildKit no usa contenedor privileged ni socket Docker. El perfil local desactiva seccomp/AppArmor sólo en su contenedor rootless y usa `--oci-worker-no-process-sandbox`; el driver CSI requiere sus privilegios oficiales de nodo. Los datos sensibles del pipeline viven en `emptyDir` de memoria y se truncan al terminar.

## Conservación y limpieza posterior

La demo se detuvo completamente el 10 de octubre de 2026. No borrar el directorio privado: contiene claves de recuperación y volúmenes dependen de los clústeres. Cuando el usuario autorice retirar la demo, borrar exclusivamente los dos clústeres kind y los contenedores `cuscatlan-registry`/`cuscatlan-git`; decidir por separado si conservar el volumen `cuscatlan-registry-data` y el directorio privado. No usar `docker system prune` ni eliminar recursos de otros proyectos.
