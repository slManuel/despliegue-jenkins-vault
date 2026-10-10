#!/usr/bin/env sh
set -eu
: "${INSTALL_ENABLED:?Set INSTALL_ENABLED=true after AWS and private access are resolved}"
[ "$INSTALL_ENABLED" = true ]
[ "$(kubectl config current-context)" = tools ] || { echo 'Expected tools context' >&2; exit 1; }
: "${CONTROLLER_IMAGE:?Published Jenkins controller image required}"
case "$CONTROLLER_IMAGE" in ghcr.io/slmanuel/jenkins-controller@sha256:*|ghcr.io/slmanuel/jenkins-controller:*) ;; *) exit 1;; esac
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl apply -f k8s/namespaces.yaml
# Secrets must be created by the operator; they are never synthesized from committed values.
kubectl -n vault get secret vault-tls >/dev/null
kubectl -n jenkins get secret jenkins-admin ghcr-pull >/dev/null
kubectl -n jenkins get configmap vault-ca >/dev/null
kubectl apply -f k8s/storage.yaml -f k8s/rbac.yaml
kubectl apply -f k8s/jenkins.yaml
kubectl set image --local -f k8s/jenkins-statefulset.yaml jenkins="$CONTROLLER_IMAGE" -o yaml | kubectl apply -f -
kubectl apply -f k8s/vault.yaml
kubectl -n jenkins rollout status statefulset/jenkins --timeout=600s
echo 'Vault initialization/unseal remains an interactive operator step. Never save root or unseal keys in this repo.'
