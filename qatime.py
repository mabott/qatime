#!/usr/bin/env python

"""qatime.py takes care of the two glue functions of our atime widget:
1) Receive UDP messages from rsyslogd, filter/process/insert into Redis
2) Set atime using touch on a container-local fs which is actually an NFS bind
mount in the container"""

import sys
import logging
import socketserver
import subprocess
import configparser
import redis

from time import sleep
from threading import Thread
from typing import Tuple

from qatime_config import load_config
from qumulo.rest_client import RestClient

logger = logging.getLogger()
listening = False


def connect_to_redis() -> "redis.Redis[bytes]":
    r = None
    try:
        r = redis.Redis(host="redis")
    except ConnectionRefusedError:
        # Wait and retry?
        while True:
            try:
                logger.debug("Connection to Redis failed, waiting for retry")
                sleep(5)
                r = redis.Redis(host="redis")
                break
            except ConnectionRefusedError:
                continue

    assert r is not None
    return r


R = connect_to_redis()


ATIME_UPDATES = {"fs_read_data", "fs_write_data", "fs_list_directory"}


def pass_message(data: str) -> bool:
    """Filters for fs_read and fs_write"""
    fields = data.split(",")
    op_type = fields[5]
    should_pass = op_type in ATIME_UPDATES
    logger.debug("op_type: %s (%s)", op_type, should_pass)
    return should_pass


def extract_keyvalue(data: str) -> Tuple[str, str]:
    fields = data.split(",")
    timestamp = fields[0]
    # if we don't strip quotes redis escapes
    file_path = fields[8].strip('"')
    logger.debug("file path: %s, timestamp: %s", file_path, timestamp)
    return file_path, timestamp


class SyslogUDPHandler(socketserver.BaseRequestHandler):
    """Listens for syslog messages, extracts info, populates Redis"""

    def handle(self) -> None:
        data = bytes.decode(self.request[0].strip())
        logger.debug("message: %s", data)
        if pass_message(data):
            file_path, timestamp = extract_keyvalue(data)
            R.set(file_path, timestamp)


def atime_setter(client: RestClient) -> None:
    while True:
        sleep(0.1)
        try:
            keys = [R.randomkey()]  # type: ignore[no-untyped-call]
        except ConnectionRefusedError:
            continue

        for key in keys:
            try:
                path = key.decode("utf-8")
            except AttributeError as e:
                break
            # get atime
            value = R.get(key)
            assert value is not None
            atime = value.decode("utf-8")
            logger.debug("Setting atime on '%s' to '%s'", path, atime)
            try:
                client.fs.set_file_attr(path=path, access_time=atime)
            except Exception as e:
                logger.debug("Failed to set atime: %s", e)
            else:
                # when the above is successful, remove it from redis
                logger.debug("Set atime")
                R.delete(key)


def main() -> None:
    logger.setLevel(logging.DEBUG)

    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    config = load_config()
    client = config.rest.make_client()
    syslog_addr = (config.syslog.host, config.syslog.port)

    listening = True
    try:
        # UDP server
        udp_server = socketserver.UDPServer(syslog_addr, SyslogUDPHandler)
        udp_thread = Thread(target=udp_server.serve_forever)
        udp_thread.daemon = True
        udp_thread.start()

        # atime setter
        atime_setter_thread = Thread(target=atime_setter, args=[client])
        atime_setter_thread.daemon = True
        atime_setter_thread.start()

        while True:
            sleep(1)

    except (IOError, SystemExit):
        raise
    except KeyboardInterrupt:
        listening = False
        udp_server.shutdown()
        udp_server.server_close()
        logger.info("Crtl+C Pressed. Shutting down.")


if __name__ == "__main__":
    main()
