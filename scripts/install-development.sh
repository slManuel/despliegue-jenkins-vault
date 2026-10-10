#!/usr/bin/env sh
set -eu
: "${INSTALL_ENABLED:?Set INSTALL_ENABLED=true after AWS and private access are resolved}"
[ "$INSTALL_ENABLED" = true ]
[ "$(kubectl config current-context)" = development ] || exit 1
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl apply -k operators/secrets-store-csi
kubectl apply -k operators/vault-csi
kubectl -n csi get configmap vault-ca >/dev/null
kubectl apply -k operators/vso
kubectl wait --for=condition=Established crd/vaultconnections.secrets.hashicorp.com crd/vaultauths.secrets.hashicorp.com crd/vaultstaticsecrets.secrets.hashicorp.com crd/secretproviderclasses.secrets-store.csi.x-k8s.io --timeout=120s
kubectl -n vault-secrets-operator-system rollout status deployment/vault-secrets-operator-controller-manager --timeout=300s
kubectl -n csi rollout status daemonset/vault-csi-provider --timeout=300s
kubectl -n kube-system rollout status daemonset/csi-secrets-store --timeout=300s
