#!/usr/bin/env python

"""qatime.py takes care of the two glue functions of our atime widget:
1) Receive UDP messages from rsyslogd, filter/process/insert into Redis
2) Set atime using touch on a container-local fs which is actually an NFS bind
mount in the container"""

import logging
import socketserver
import subprocess
import redis

from time import sleep
# Logging is threadsafe but not mp-safe
from threading import Thread
# from multiprocessing import Process

# Syslog Message Handler
LOG_FILE = 'qatime.log'
HOST = '0.0.0.0'
UDP_PORT = 1514

# atime setter
NFS_MOUNT = "/mnt/qumulo"
BATCH_SIZE = 10

listening = False

logging.basicConfig(level=logging.DEBUG, format='%(message)s', datefmt='',
                    filename=LOG_FILE, filemode='a')

R = redis.Redis(host='redis')


class SyslogUDPHandler(socketserver.BaseRequestHandler):
    """Listens for syslog messages, extracts info, populates Redis"""
    def handle(self):
        data = bytes.decode(self.request[0].strip())
        if pass_message(data):
            extract_keyvalue(str(data))


def extract_keyvalue(data):
    list = data.split(',')
    timestamp = list[0]
    file_path = list[8].strip('"')  # if we don't strip quotes redis escapes
    logging.info(list)
    logging.info(file_path)
    logging.info(timestamp)
    R.set(file_path, timestamp)


def pass_message(data):
    """filters for fs_read and fs_write, returns True for those"""
    list = data.split(',')
    op_type = list[5]
    logging.info(op_type)
    return op_type in ['fs_read_data', 'fs_write_data', 'fs_list_directory']


def atime_setter():
    while True:
        sleep(0.1)
        keys = [R.randomkey()]
        logging.debug(keys)
        for key in keys:
            try:
                path = key.decode('utf-8')
            except AttributeError as e:
                logging.info("atime_setter() got")
                logging.info(e)
                continue
            local_path = NFS_MOUNT + path
            logging.debug(local_path)
            # get atime
            value = R.get(key)
            try:
                atime = value.decode('utf-8')
            except AttributeError as e:
                logging.info("atime_setter() value can't be decoded")
                logging.info(e)
                continue
            logging.debug(atime)
            try:
                logging.info("Attempting to touch " + local_path + " with atime " + atime)
                subprocess.check_call(['touch', '-a', '-d', atime, local_path])
                # when the above is successful, remove it from redis
                R.delete(key)
            except subprocess.CalledProcessError as e:
                logging.info("Failed to delete a key")
                logging.info(e)
            stuff = R.get(key)
            try:
                logging.info("STUFF:" + stuff.decode('utf-8'))
            except AttributeError as e:
                logging.info(e)


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
        print ("Crtl+C Pressed. Shutting down.")
