#!/usr/bin/env bash
set -e

IMAGE_NAME=kube-service-selectors
REGISTRY=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -r) REGISTRY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

GIT_HASH=${GIT_HASH:-$(git rev-parse HEAD)}

docker build -t "${IMAGE_NAME}:build" \
  --label commit="${GIT_HASH}" \
  --label version="${VERSION:-none}" .

if [[ -n "${REGISTRY}" ]]; then
  REMOTE_TAG="${REGISTRY}/${IMAGE_NAME}:${GIT_HASH}"
  docker tag "${IMAGE_NAME}:build" "${REMOTE_TAG}"
  docker push "${REMOTE_TAG}"
fi
