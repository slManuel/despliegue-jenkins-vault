#!/usr/bin/env sh
# Configuración compartida. Ejecutar manualmente con token administrativo temporal.
set -eu
set +x
: "${TOOLS_ISSUER:?Tools EKS issuer required}"
: "${DEVELOPMENT_ISSUER:?Development EKS issuer required}"
: "${QA_ISSUER:?QA EKS issuer required}"
: "${PRODUCTION_ISSUER:?Production EKS issuer required}"
for issuer in "$TOOLS_ISSUER" "$DEVELOPMENT_ISSUER" "$QA_ISSUER" "$PRODUCTION_ISSUER"; do
  case "$issuer" in https://oidc.eks.us-east-1.amazonaws.com/id/*) ;; *) echo 'Unexpected EKS issuer' >&2; exit 1;; esac
done
[ "$TOOLS_ISSUER" != "$DEVELOPMENT_ISSUER" ] && [ "$TOOLS_ISSUER" != "$QA_ISSUER" ] && [ "$TOOLS_ISSUER" != "$PRODUCTION_ISSUER" ]
[ "$DEVELOPMENT_ISSUER" != "$QA_ISSUER" ] && [ "$DEVELOPMENT_ISSUER" != "$PRODUCTION_ISSUER" ] && [ "$QA_ISSUER" != "$PRODUCTION_ISSUER" ]
vault secrets list -format=json | jq -e 'has("kv/")' >/dev/null || vault secrets enable -path=kv kv-v2
vault auth list -format=json | jq -e 'has("deployment/")' >/dev/null || vault auth enable -path=deployment jwt
vault write auth/deployment/config oidc_discovery_url="$TOOLS_ISSUER" bound_issuer="$TOOLS_ISSUER"
configure_environment() {
  target=$1
  issuer=$2
  vault policy write "jenkins-$target" "vault/environments/$target/jenkins-policy.hcl"
  vault policy write "microservicio-$target" "vault/environments/$target/microservicio-policy.hcl"
  vault auth list -format=json | jq -e --arg mount "$target/" 'has($mount)' >/dev/null || vault auth enable -path="$target" jwt
  vault write "auth/$target/config" oidc_discovery_url="$issuer" bound_issuer="$issuer"
  vault write "auth/deployment/role/jenkins-$target" role_type=jwt user_claim=sub bound_subject=system:serviceaccount:jenkins:jenkins-pipeline bound_audiences=vault token_policies="jenkins-$target" token_ttl=5m token_max_ttl=5m
  vault write "auth/$target/role/microservicio" role_type=jwt user_claim=sub bound_subject="system:serviceaccount:$target:microservicio" bound_audiences=vault token_policies="microservicio-$target" token_ttl=5m token_max_ttl=5m
  # Inicializa/reemplaza exclusivamente datos de evaluación, nunca secretos de producción reales.
  vault kv put "kv/environments/$target/app" DEMO_MESSAGE="demostracion-$target" FEATURE_FLAG=enabled
  vault kv put "kv/environments/$target/config" property="demo.property=configuracion-$target-desde-CSI"
}
configure_environment development "$DEVELOPMENT_ISSUER"
configure_environment qa "$QA_ISSUER"
configure_environment production "$PRODUCTION_ISSUER"
echo 'Three environment policies, JWT mounts and demonstration records configured; values omitted.'
