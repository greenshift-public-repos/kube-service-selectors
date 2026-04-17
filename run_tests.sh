#!/usr/bin/env bash
set -e

TEST_IMAGE=kube-service-selectors-tests:build

bash build.sh
docker build -t ${TEST_IMAGE} -f Dockerfile_tests .

echo "Black check>>>"
docker run -i --entrypoint black --rm ${TEST_IMAGE} --check .
echo "<<<Black check"

echo "PEP8 tests>>>"
docker run -i --entrypoint pycodestyle --rm ${TEST_IMAGE} --show-pep8 --exclude=.venv .
echo "<<<PEP8 tests"

echo "Pytest>>>"
docker run -i -v $PWD/reports:/usr/src/app/reports \
  --entrypoint pytest --rm ${TEST_IMAGE}
echo "<<<Pytest"

docker rmi ${TEST_IMAGE}
