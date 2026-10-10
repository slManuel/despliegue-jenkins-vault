# Matriz de evaluación — 40,25 puntos posibles

Fuente: PRUEBA TÉCNICA DEVOPS.pdf facilitado por el usuario (dos páginas). Esta matriz traza requisitos al código, **no asigna puntos obtenidos**. Estado al 10/10/2026: implementación preparada; pruebas cloud bloqueadas por cuenta AWS/EC2/Fleet y acceso privado pendiente.

| Requisito | Puntos | Evidencia de código | Comprobación disponible / pendiente |
|---|---:|---|---|
| IaC modular y legible | 3,5 | infra-red-compartida, infra-jenkins-vault, infra-microservicio; módulos por responsabilidad | fmt/init backend=false/validate; plan/apply micro pendiente |
| Pipeline Jenkins automatizado | 3 | devops-java-service/Jenkinsfile; JCasC y plugins en este repo | imágenes/plugins construidos, Groovy compila; job integrado pendiente |
| Lectura segura de Vault antes del build | 3 | scripts/read-vault.sh; token SA proyectado, JWT, CA, revocación; env antes del test/build | sintaxis shell; login real pendiente |
| Build, push, deploy y rollback | 2,5 | Dockerfile, Jenkinsfile, scripts/deploy.sh y rollback.sh | Docker/HTTP local; GHCR, rollout y rollback integrado pendientes |
| Jenkins autenticado ante Vault | 2 | auth/deployment JWT con issuer tools y bound_subject jenkins-pipeline | políticas/configuración preparada; autenticación pendiente |
| Políticas/token/auth mínimos | 1 | vault/*.hcl; TTL5m; mounts separados por issuer; sin token root en pipeline | revisión de código; prueba de denegación fuera de paths pendiente |
| Vault Secrets Operator | 2 | operators/vso1.6.0; micro k8s/vault.yaml; FEATURE_FLAG env | render y CR schemas válidos; sincronización/rotación pendientes |
| CSI Vault provider | 1 | driver1.6.1/provider1.7.4; SecretProviderClass; volumen properties | render/schema; archivo montado pendiente |
| SA para inyección en pipeline | 1 | jenkins-pipeline, JWT proyectado aud=vault/600s | manifiesto válido; login y subject rechazado de otro SA pendientes |
| Probes, namespaces, RBAC y separación | 4 | tools vs development; identities, probes, requests/limits; API privada | schema42 recursos estándar tools y11micro; runtime pendiente |
| Manifiestos robustos | 1 | propios StatefulSets/Deployment, PVC cifrado Retain, TLS, políticas de seguridad | schemas/render válidos; PVC, reinicios/unseal pendientes |
| Dos réplicas y balanceador | 1,75 | micro deployment replicas2/service NLB restringido | YAML válido; pods/targets/DNS pendientes |
| Endpoint de env inyectada | 2 | Main.java /api/secret; opción EXPOSE_DEMO_VALUE | pruebas HTTP ambos modos pasan; demo en EKS pendiente |
| Endpoint de propiedad local | 3 | Main.java /api/config; CSI application.properties | prueba HTTP archivo local pasa; CSI real pendiente |
| Instrucciones de clústeres | 3,5 | READMEs IaC y OPERACION.md | guía de recuperación de estado, acceso privado y orden disponible; ejecución pendiente |
| Documentación pipeline/Vault | 4 | READMEs micro/herramientas, OPERACION.md, políticas | procedimientos y evidencias locales; capturas/salidas cluster pendientes |
| Diagrama | 2 | Mermaid en README de herramientas | revisado contra rutas TLS/NLB/API privado |
| **Total posible** | **40,25** | | **No equivale a puntuación obtenida** |

Extensión opcional de CronJob para exportar eventos de kubelet: no implementada, no se declara cubierta.

## Evidencia local reproducible

- Java21 SmokeTest: PASS en HTTP readiness, JSON escaping, variable antes de build, redacción, demostración explícita, propiedad local y método405.
- Docker build: servicio Java, Jenkins con plugins y agente Java21/kubectl construidos correctamente.
- Jenkinsfile: compilación sintáctica Groovy2.4.21 del Jenkins2.580.1; no es validación semántica del pipeline ni prueba del plugin en un clúster.
- Kustomize: VSO20 recursos, provider7 y driver7. Kubeconform estándar: 42 válidos, 10 CRD upstream omitidos explícitamente (no hay esquema estándar disponible). CR de aplicación: 11 válidos contra schemas Kubernetes1.36 y schemas extraídos de CRD versionados.
- Terraform micro: 16 recursos explícitos; fmt y validate correctos. `init -backend=false` no accede al estado S3 ni demuestra permisos cloud.

## Evidencia integrada que falta

Tras resolver AWS y disponer de acceso privado: aplicar con estado existente, nodos Ready, PVC Bound, init/unseal Vault, issuerJWT tools/micro, Secret VSO reconciliado, archivo CSI presente, push privado por digest, deployment2 Ready, respuestas de demo por CIDR permitido y rollback de una actualización fallida. Capturar únicamente datos de demostración y metadatos. No compartir valores Vault reales, estados, tokens, kubeconfig ni claves.
