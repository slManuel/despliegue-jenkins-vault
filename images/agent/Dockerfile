FROM jenkins/inbound-agent:jdk21@sha256:64a27e807d216d527a7f5224e6ff9733b5cbd8650db3b5dfd0aea3b94949460f
USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl jq git ca-certificates && rm -rf /var/lib/apt/lists/*
ARG KUBECTL_VERSION=v1.36.0
RUN curl --fail --location --silent --show-error -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && curl --fail --location --silent --show-error -o /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256" \
 && echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" | sha256sum --check \
 && chmod 0755 /usr/local/bin/kubectl && rm /tmp/kubectl.sha256
USER jenkins
