#!/bin/bash

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 tyk-product and version"
  echo "       Must provide product and version like this tyk-gateway:v5.8.2 or tyk-mdcb-docker:v2.8.1"
  echo "       The resulting image will be called that with -custom added. But it will not have the tykio/ at the start"
  echo "       export MINIKUBE=something to build inside minikube"
  exit 1
fi

PRODUCT_VERSION="$1"

if [[ -n $MINIKUBE ]]; then
  eval $(minikube docker-env)
fi

docker image pull tykio/$PRODUCT_VERSION
PORT=$(docker inspect --format='{{range $key, $value := .Config.ExposedPorts}}{{$key}} {{end}}' tykio/$PRODUCT_VERSION)
if [[ -z $PORT ]]; then
  PORT=8080
fi
WORKDIR=$(docker inspect --format='{{.Config.WorkingDir}}' tykio/$PRODUCT_VERSION)
ENTRYPOINT=$(docker inspect --format='{{json .Config.Entrypoint}}' tykio/$PRODUCT_VERSION)
CMD=$(docker inspect --format='{{json .Config.Cmd}}' tykio/$PRODUCT_VERSION)

cat > Dockerfile << EOF
FROM debian:trixie-slim AS debian
FROM tykio/$PRODUCT_VERSION AS tyk-product

ENV DEBIAN_FRONTEND=noninteractive

FROM scratch
COPY --from=debian / /
COPY --from=tyk-product /opt/ /opt

RUN apt-get update \
    && apt-get dist-upgrade -y ca-certificates

# Clean up caches, unwanted .a and .o files
RUN rm -rf /root/.cache \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /usr/include/* /var/cache/apt/archives /var/lib/{apt,dpkg,cache,log} \
    && find /usr/lib -type f -name '*.a' -o -name '*.o' -delete

ARG PORT=8080
EXPOSE $PORT

ARG WORKDIR=/
WORKDIR $WORKDIR

ARG ENTRYPOINT='["/bin/sh"]'
ENTRYPOINT $ENTRYPOINT

ARG CMD='[""]'
CMD $CMD
EOF

docker image build --tag $PRODUCT_VERSION-custom .

