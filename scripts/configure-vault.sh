#!/usr/bin/env sh
# Run from this repository on a private-access workstation with Vault CLI and jq.
# Authenticate interactively with a temporary administrative token using the token helper.
set -eu
set +x
# Authenticate with vault login -no-print; token helper is supported.
: "${TOOLS_ISSUER:?EKS deployment cluster OIDC issuer required}"
: "${DEVELOPMENT_ISSUER:?EKS microservice cluster OIDC issuer required}"
case "$TOOLS_ISSUER:$DEVELOPMENT_ISSUER" in https://oidc.eks.us-east-1.amazonaws.com/id/*:https://oidc.eks.us-east-1.amazonaws.com/id/*) ;; *) echo 'Unexpected EKS issuer' >&2; exit 1;; esac
vault secrets list -format=json | jq -e 'has("kv/")' >/dev/null || vault secrets enable -path=kv kv-v2
vault policy write jenkins vault/jenkins-policy.hcl
vault policy write microservicio vault/microservicio-policy.hcl
vault auth list -format=json | jq -e 'has("deployment/")' >/dev/null || vault auth enable -path=deployment jwt
vault auth list -format=json | jq -e 'has("development/")' >/dev/null || vault auth enable -path=development jwt
vault write auth/deployment/config oidc_discovery_url="$TOOLS_ISSUER" bound_issuer="$TOOLS_ISSUER"
vault write auth/development/config oidc_discovery_url="$DEVELOPMENT_ISSUER" bound_issuer="$DEVELOPMENT_ISSUER"
vault write auth/deployment/role/jenkins role_type=jwt user_claim=sub bound_subject=system:serviceaccount:jenkins:jenkins-pipeline bound_audiences=vault token_policies=jenkins token_ttl=5m token_max_ttl=5m
vault write auth/development/role/microservicio role_type=jwt user_claim=sub bound_subject=system:serviceaccount:development:microservicio bound_audiences=vault token_policies=microservicio token_ttl=5m token_max_ttl=5m
# These are deliberately non-sensitive assessment data, never production credentials.
vault kv put kv/demo/app DEMO_MESSAGE=demostracion-cuscatlan FEATURE_FLAG=enabled
vault kv put kv/demo/config property='demo.property=configuracion-desde-CSI'
echo 'JWT roles, least-privilege policies and demonstration records configured.'
