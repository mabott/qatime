#!/usr/bin/env bash

# Redis container
docker run -d \
    --network qatime --network-alias redis \
    --cidfile /tmp/docker_redis.cid \
    redis

rm /tmp/docker_redis.cid
