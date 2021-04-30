import sys, os
import redis

import passthroughfs
from passthroughfs import init_logging, parse_args

import pyfuse3
import logging
import stat as stat_m
from pyfuse3 import FUSEError
from datetime import datetime
import trio

import faulthandler
faulthandler.enable()

R = redis.Redis()
log = logging.getLogger(__name__)


class QOperations(passthroughfs.Operations):
    """We need to get at source so we can normalize the directory path in our
    call to redis, and the _getattr() method is a bit dense, so apologies for
    all this copypasta"""
    def __init__(self, source):
        super().__init__(source)
        self._source = source

    """We only need to replace st_atime_ns in this call
    need to get it from redis based on path"""
    def _getattr(self, path=None, fd=None):
        assert fd is None or path is None
        assert not(fd is None and path is None)
        try:
            if fd is None:
                stat = os.lstat(path)
            else:
                stat = os.fstat(fd)
        except OSError as exc:
            raise FUSEError(exc.errno)

        entry = pyfuse3.EntryAttributes()
        for attr in ('st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                     'st_rdev', 'st_size', 'st_atime_ns', 'st_mtime_ns',
                     'st_ctime_ns'):
            setattr(entry, attr, getattr(stat, attr))
        # If this is a directory, add a trailing slash before lookup to match
        # the Qumulo path from Audit logs
        if stat_m.S_ISDIR(stat.st_mode): # actually based on NFS stat
            path += '/'
        # Normalize path cuz the local path != the Qumulo path from Audit logs
        real_path = self._normalize_redis_path(path)
        try:
            real_atime = epoch_seconds_to_nanoseconds(get_atime(real_path))
        except AttributeError:
            # no atime exists in our db yet, so make one up from existing times
            real_atime = epoch_seconds_to_nanoseconds(max(stat.st_mtime, stat.st_ctime))
        setattr(entry, 'st_atime_ns', real_atime)
        # The rest of this method is copy/paste from passthroughfs.py
        entry.generation = 0
        entry.entry_timeout = 0
        entry.attr_timeout = 0
        entry.st_blksize = 512
        entry.st_blocks = ((entry.st_size+entry.st_blksize-1) // entry.st_blksize)

        return entry

    def _normalize_redis_path(self, local_path):
        try:
            real_path = local_path.replace(self._source, '')
        except AttributeError as e:
            log.debug(str(e))
        return real_path

def get_atime(path):
    """Ask redis for the atime stamp, convert to epoch seconds, return"""
    atime = R.get(path).decode('utf-8')
    epoch_atime = iso_to_epoch(atime)
    return epoch_atime

def iso_to_epoch(iso_timestamp):
    iso_format = '%Y-%m-%dT%H:%M:%S.%fZ'
    utc_time = datetime.strptime(iso_timestamp, iso_format)
    epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return epoch_time

def epoch_seconds_to_nanoseconds(seconds):
    """explicit is better than implicit I guess?"""
    return(int(seconds) * 1000000000)

def main():
    options = parse_args(sys.argv[1:])
    init_logging(options.debug)
    # Just need to swap out Operations() for QOperations()
    # operations = Operations(options.source)
    operations = QOperations(options.source)
    # Everything else comes from passthroughfs.py
    log.debug('Mounting...')
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=passthroughfs')
    if options.debug_fuse:
        fuse_options.add('debug')
    pyfuse3.init(operations, options.mountpoint, fuse_options)

    try:
        log.debug('Entering main loop..')
        trio.run(pyfuse3.main)
    except:
        pyfuse3.close(unmount=False)
        raise

    log.debug('Unmounting..')
    pyfuse3.close()


if __name__ == '__main__':
    main()
