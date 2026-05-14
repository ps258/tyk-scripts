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

function createGatewayDockerfile() {
  cat > Dockerfile << EOF
FROM tykio/$PRODUCT_VERSION AS tyk-gateway
FROM busybox:stable AS busybox

FROM scratch
COPY --from=busybox / /
COPY --from=tyk-gateway /opt/tyk-gateway /opt/tyk-gateway/
COPY --from=tyk-gateway /lib/x86_64-linux-gnu/libdl.so.2 /lib/x86_64-linux-gnu/

ARG PORT=8080
EXPOSE $PORT
WORKDIR /opt/tyk-tyk-gateway/
ENTRYPOINT ["/opt/tyk-tyk-gateway/tyk"]
CMD ["--conf=/opt/tyk-gateway/tyk.conf"]
EOF
}

function createMDCBdockerfile() {
  cat > Dockerfile << EOF
FROM tykio/$PRODUCT_VERSION AS mdcb
FROM busybox:stable AS busybox

FROM scratch
COPY --from=busybox / /
COPY --from=mdcb /opt/tyk-sink /opt/tyk-sink/

COPY --chown=999:999 ./tyk-sink /opt/tyk-sink/tyk-sink

ARG PORT=9090
EXPOSE $PORT
WORKDIR /opt/tyk-sink/
ENTRYPOINT ["/opt/tyk-sink/tyk-sink"]
CMD ["--conf=/opt/tyk-sink/tyk_sink.conf"]
EOF
}

function createPortalDockerfile() {
  echo PORT=$PORT
  echo WORKDIR=$WORKDIR
  echo ENTRYPOINT=$ENTRYPOINT
  echo CMD=$CMD
  cat > Dockerfile << EOF
FROM tykio/$PRODUCT_VERSION AS portal
FROM busybox:stable AS busybox

FROM scratch
COPY --from=busybox / /
COPY --from=portal /opt /opt/
COPY --from=portal /usr /usr/
COPY --from=portal /etc /etc/
COPY --from=portal /lib/x86_64-linux-gnu/libdl.so.2 /lib/x86_64-linux-gnu/

ARG PORT=3001
EXPOSE $PORT
WORKDIR /opt/portal-sink/
ENTRYPOINT ["/opt/portal/dev-portal"]
CMD ["--conf=/opt/portal/portal.conf"]
EOF
}

if ! docker image pull tykio/$PRODUCT_VERSION; then
  echo "[FATAL]Cannot pull image tykio/$PRODUCT_VERSION"
  exit 1
fi
export PORT=$(docker inspect --format='{{range $key, $value := .Config.ExposedPorts}}{{$key}} {{end}}' tykio/$PRODUCT_VERSION)
if [[ -z $PORT ]]; then
  export PORT=8080
fi
export WORKDIR=$(docker inspect --format='{{.Config.WorkingDir}}' tykio/$PRODUCT_VERSION)
export ENTRYPOINT=$(docker inspect --format='{{json .Config.Entrypoint}}' tykio/$PRODUCT_VERSION)
export CMD=$(docker inspect --format='{{json .Config.Cmd}}' tykio/$PRODUCT_VERSION)

echo PORT=$PORT
echo WORKDIR=$WORKDIR
echo ENTRYPOINT=$ENTRYPOINT
echo CMD=$CMD

case $PRODUCT_VERSION in
  tyk-gateway*)
    createGatewayDockerfile
    ;;
  tyk-mdcb*)
    createMDCBdockerfile
    ;;
  portal*)
    createPortalDockerfile
    ;;
  *)
    echo "[FATAL]unsupported product $PRODUCT_VERSION"
    exit 1
    ;;
esac

docker image build --tag $PRODUCT_VERSION-custom .

