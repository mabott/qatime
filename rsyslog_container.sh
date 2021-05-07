#!/usr/bin/env bash

docker network create qatime

# Rsyslogd container
docker run -d \
    --network qatime --network-alias rsyslog \
    -p 514:514 \
    --cidfile /tmp/docker_rsyslog.cid \
    jumanjiman/rsyslog
# configure rsyslog container then bounce it
docker cp 60-qumulo.conf `cat /tmp/docker_rsyslog.cid`:/etc/rsyslog.d
docker exec -it --user root `cat /tmp/docker_rsyslog.cid` \
    chown root:root /etc/rsyslog.d/60-qumulo.conf
docker restart `cat /tmp/docker_rsyslog.cid`

# clean up temp files
rm /tmp/docker_rsyslog.cid
