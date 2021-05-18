# qatime

A small widget for maintaining atime metadata on a Qumulo cluster.

Depends on `redis` and `rsyslog`, but the included `docker-compose.yml` can build the appropriate 
containers and wire them together properly. Rsyslog needs to listen for Audit messages coming from
Qumulo, and the qatime container needs an NFS mount to the Qumulo cluster with admin-level permissions.

The standard atime attribute is not exposed by the Qumulo API, nor is it updated when appropriate
(e.g. file read, directory listing). It _is_ used when we respond to a `stat()` call, and can be
set with `touch -a $timestamp $path_to_file`.

This widget uses a Qumulo cluster's Audit stream of syslog messages to recognize qualifying
events and set the atime appropriately.

## Installation

Pull the code from this repo:

`$ git clone https://github.com/mabott/qatime.git`

This should not be necessary in most cases, but if it is edit `qatime_config.ini` to match your 
environment.

Update docker-compose.yml to reflect the correct address of one node of your Qumulo cluster:

```yml
volumes:
  qumulo:
    driver_opts:
      type: "nfs"
      o: "addr=**192.168.240.130**,hard,intr,rw,tcp,nfsvers=3"
      device: ":/"
```

Fire up the containers:

`$ docker-compose up --build`

Test it out:

```bash
(qatime) mbott@lol:/mnt/qumulo$ stat Demo | grep Access
Access: (0775/drwxrwxr-x)  Uid: ( 1000/   mbott)   Gid: ( 1000/   mbott)
Access: 2021-05-18 00:17:39.474255000 +0000
(qatime) mbott@lol:/mnt/qumulo$ ls Demo
atestfile.txt  testfile
(qatime) mbott@lol:/mnt/qumulo$ stat Demo | grep Access
Access: (0775/drwxrwxr-x)  Uid: ( 1000/   mbott)   Gid: ( 1000/   mbott)
Access: 2021-05-18 01:07:07.722120000 +0000
(qatime) mbott@lol:/mnt/qumulo$
```

## Known Issues

1. Redis might not be necessary anymore. The original intent was to use Redis as a database of paths
and atime results. Currently it's only used as a cache.
   
1. This has not been adequately tested against interesting characters or character sets in the
path names that get sent by Qumulo Audit.
   
1. This needs more testing, particularly e2e testing to validate the whole environment. It's unlikely
that `redis` or `rsyslog` break with updates, given their stability, but you never know.
