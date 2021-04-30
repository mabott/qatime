import sys
import logging
import redis
import subprocess

from time import sleep

NFS_MOUNT = '/mnt/nfs'

LOG = logging.getLogger(__name__)
R = redis.Redis()


def main():
    try:
        while True:
            sleep(0.1)
            # grab a redis keyvalue off the bottom of redis
            key = R.randomkey()
            try:
                path = key.decode('utf-8')
            except AttributeError as e:
                LOG.debug(e)
                continue
            local_path = NFS_MOUNT + path
            LOG.debug(local_path)
            # get ctime
            value = R.get(key)
            atime = value.decode('utf-8')
            LOG.debug(atime)
            subprocess.check_call(['touch', '-a', '-d', atime, local_path])
            # when the above is successful, remove it from redis
            R.delete(key)
            stuff = R.get(key)
            print("STUFF:", stuff)

    except KeyboardInterrupt:
        LOG.info("CTRL-C Detected, exiting")
        sys.exit(0)


if __name__ == '__main__':
    main()
