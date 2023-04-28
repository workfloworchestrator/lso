#!/usr/bin/env bash

goat_name="goat-lso"
goat_image="goat/lso"
goat_tag="1.0"

if [[ $(docker image list | grep "${goat_image}" | grep -c "${goat_tag}") -eq 0 ]]; then
  docker build -f docker/Dockerfile -t ${goat_image}:${goat_tag} .
fi
if [[ $(docker ps -a | grep -c "${goat_image}:${goat_tag}") -eq 0 ]]; then
  docker run -d -p 44444:44444 --name ${goat_name} ${goat_image}:${goat_tag} >/dev/null 2>&1
fi
if [[ "$( docker container inspect -f '{{.State.Status}}' ${goat_name} )" != "running" ]]; then
  docker start ${goat_name} >/dev/null 2>&1
fi

sleep 1

# Check endpoints
curl -f http://localhost:44444/docs >/dev/null 2>&1
if [[ $? -eq 0 ]]; then
  echo "LSO is running. OpenAPI available at http://localhost:44444/docs"
else
  echo "LSO is not running"
fi
