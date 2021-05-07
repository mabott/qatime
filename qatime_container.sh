#!/usr/bin/env bash

docker build -t qatime .

# qatime container, use local Dockerfile
docker run -d \
    --network qatime --network-alias qatime \
    --cidfile /tmp/docker_qatime.cid \
    --mount type=volume,dst=/mnt/qumulo,volume-driver=local,volume-opt=type=nfs,\"volume-opt=o=nfsvers=3,tcp,rw,hard,intr,addr=192.168.11.155\",volume-opt=device=:/ \
    qatime

# clean up
rm /tmp/docker_qatime.cid
