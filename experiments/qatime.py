import sys, os
import redis

import passthroughfs
from passthroughfs import init_logging, parse_args, main

import pyfuse3
from argparse import ArgumentParser
import errno
import logging
import stat as stat_m
from pyfuse3 import FUSEError
from os import fsencode, fsdecode
from collections import defaultdict
from datetime import datetime
import trio

import faulthandler
faulthandler.enable()

R = redis.Redis()
log = logging.getLogger(__name__)


class QOperations(passthroughfs.Operations):
    """We need to get at source for a proper getattr"""
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
        # If this is a directory, add a trailing slash before lookup
        if stat_m.S_ISDIR(stat.st_mode):
            path += '/'
        # Add st_atime_ns
        print("Before atime injection:", entry.st_atime_ns)
        # Normalize path
        real_path = self._normalize_redis_path(path)
        print("Original path is:", path)
        print("We think the real path is:", real_path)
        try:
            real_atime = epoch_seconds_to_nanoseconds(self._get_atime(real_path))
            print("Redis sez:", real_atime)
        except AttributeError:
            # no atime exists in our db yet, so make one up
            real_atime = epoch_seconds_to_nanoseconds(max(stat.st_mtime, stat.st_ctime))
            print("Qumulo sez:", real_atime)
        setattr(entry, 'st_atime_ns', real_atime)
        print("entry sez: ", entry.st_atime_ns)
        entry.generation = 0
        entry.entry_timeout = 0
        entry.attr_timeout = 0
        entry.st_blksize = 512
        entry.st_blocks = ((entry.st_size+entry.st_blksize-1) // entry.st_blksize)

        return entry

    def _get_atime(self, path):
        """Ask redis for the atime stamp, convert to epoch seconds, return"""
        print("get atime for path:", path)
        atime = R.get(path).decode('utf-8')
        epoch_atime = iso_to_epoch(atime)
        return epoch_atime

    def _normalize_redis_path(self, local_path):
        print("self._source:", self._source)
        print("trying to normalize local_path", local_path)
        print("local_path type:", type(local_path))
        print("self._source type:", type(self._source))
        real_path = local_path.replace(self._source, '')
        return real_path


def iso_to_epoch(iso_timestamp):
    iso_format = '%Y-%m-%dT%H:%M:%S.%fZ'
    utc_time = datetime.strptime(iso_timestamp, iso_format)
    epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return epoch_time

def epoch_seconds_to_nanoseconds(seconds):
    return(int(seconds) * 1000000000)


def main():
    options = parse_args(sys.argv[1:])
    init_logging(options.debug)
    # operations = Operations(options.source)
    operations = QOperations(options.source)

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
