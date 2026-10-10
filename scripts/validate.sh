#!/usr/bin/env sh
set -eu
mkdir -p build
for name in vso vault-csi secrets-store-csi; do
  kubectl kustomize "operators/$name" > "build/$name.yaml"
done
for script in scripts/*.sh; do sh -n "$script"; done
docker run --rm -v "$PWD:/work:ro" ghcr.io/yannh/kubeconform:v0.8.0 -strict -summary -skip CustomResourceDefinition -kubernetes-version 1.36.0 /work/k8s /work/build
