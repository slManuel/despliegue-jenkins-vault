#!/usr/bin/env sh
# Generates local files only. Do not commit local/ or print its contents.
set -eu
umask 077
[ ! -e local/tls ] || { echo 'local/tls already exists; refusing to overwrite keys' >&2; exit 1; }
mkdir -p local/tls
openssl req -x509 -newkey rsa:3072 -nodes -days 365 -subj '/CN=Assessment Vault CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign' -keyout local/tls/ca.key -out local/tls/ca.crt
openssl req -newkey rsa:3072 -nodes -subj '/CN=vault.vault.svc.cluster.local' -keyout local/tls/tls.key -out local/tls/tls.csr
cat > local/tls/extensions.cnf <<'CONFIG'
subjectAltName=DNS:vault.vault.svc.cluster.local,DNS:vault.vault.svc,DNS:vault,DNS:localhost
extendedKeyUsage=serverAuth
basicConstraints=critical,CA:FALSE
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
keyUsage=critical,digitalSignature,keyEncipherment
CONFIG
openssl x509 -req -in local/tls/tls.csr -CA local/tls/ca.crt -CAkey local/tls/ca.key -CAcreateserial -days 90 -extfile local/tls/extensions.cnf -out local/tls/tls.crt
openssl verify -CAfile local/tls/ca.crt local/tls/tls.crt
