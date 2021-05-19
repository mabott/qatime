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

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

config = configparser.ConfigParser()
config.read('qatime_config.ini')
LOG_FILE = config['syslog']['LOG_FILE']
HOST = config['syslog']['HOST']
UDP_PORT = int(config['syslog']['UDP_PORT'])

NFS_MOUNT = config['atime']['NFS_MOUNT']
BATCH_SIZE = int(config['atime']['BATCH_SIZE'])

listening = False

R = None
try:
    R = redis.Redis(host='redis')
except ConnectionRefusedError:
    # Wait and retry?
    while True:
        try:
            logger.debug("Connection to Redis failed, waiting for retry")
            sleep(5)
            R = redis.Redis(host='redis')
            break
        except ConnectionRefusedError:
            continue


ATIME_UPDATES = ['fs_read_data', 'fs_write_data', 'fs_list_directory']

class SyslogUDPHandler(socketserver.BaseRequestHandler):
    """Listens for syslog messages, extracts info, populates Redis"""
    def handle(self):
        data = bytes.decode(self.request[0].strip())
        logger.debug(data)
        if pass_message(data):
            file_path, timestamp = extract_keyvalue(str(data))
            logging.debug(file_path)
            logging.debug(timestamp)
            R.set(file_path, timestamp)


def extract_keyvalue(data):
    list = data.split(',')
    timestamp = list[0]
    file_path = list[8].strip('"')  # if we don't strip quotes redis escapes
    logger.debug(list)
    logger.debug(file_path)
    logger.debug(timestamp)
    return file_path, timestamp


def pass_message(data):
    """filters for fs_read and fs_write, returns True for those"""
    list = data.split(',')
    op_type = list[5]
    logger.debug(op_type)
    return op_type in ATIME_UPDATES


def atime_setter():
    while True:
        sleep(0.1)
        keys = [R.randomkey()]
        # print("Keys: " + str(keys))
        for key in keys:
            try:
                path = key.decode('utf-8')
            except AttributeError as e:
                # print("atime_setter() got")
                # print(e)
                break
            local_path = NFS_MOUNT + path
            logger.debug(local_path)
            # get atime
            value = R.get(key)
            atime = value.decode('utf-8')
            logger.debug(atime)
            try:
                logger.debug("Attempting to touch " + local_path + " with atime " + atime)
                subprocess.check_call(['touch', '-a', '-d', atime, local_path])
                # when the above is successful, remove it from redis
                R.delete(key)
            except subprocess.CalledProcessError as e:
                logger.debug("Failed to delete a key")
                logger.debug(e)


if __name__ == "__main__":
    listening = True
    try:
        # UDP server
        udpServer = socketserver.UDPServer((HOST, UDP_PORT), SyslogUDPHandler)
        udpThread = Thread(target=udpServer.serve_forever)
        udpThread.daemon = True
        udpThread.start()

        # atime setter
        atimeSetterThread = Thread(target=atime_setter)
        atimeSetterThread.daemon = True
        atimeSetterThread.start()

        while True:
            sleep(1)

    except (IOError, SystemExit):
        raise
    except KeyboardInterrupt:
        listening = False
        udpServer.shutdown()
        udpServer.server_close()
        logger.info("Crtl+C Pressed. Shutting down.")
