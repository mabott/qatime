import qatime

import os
import configparser
import subprocess
import logging
import logging.handlers
import time

from time import sleep
from unittest import TestCase
from qumulo.rest_client import RestClient

config = configparser.ConfigParser()
config.read('qatime_config.ini')
TEST_PATH = config['test']['TEST_PATH']
QADDRESS = config['qumulo']['QADDRESS']
QPORT = config['qumulo']['QPORT']
QLOGIN = config['qumulo']['QLOGIN']
QPASS = config['qumulo']['QPASS']

# This is the format forwarded by Tommy's rsyslog config
FS_LIST_DIRECTORY='2021-05-18T00:02:22.357726Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_list_directory,ok,6,"/Demo/",""'
FS_READ_METADATA='2021-05-18T00:02:22.355392Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_read_metadata,ok,6,"/Demo/",""'
FS_READ_DATA='2021-05-18T00:44:20.362001Z,qumulo-1,qumulo  192.168.240.129,"admin",api,fs_read_data,ok,7,"/Demo/testfile",""'
FS_WRITE_METADATA='2021-05-18T00:44:20.395482Z,qumulo-1,qumulo  192.168.240.129,"0",nfs3,fs_write_metadata,ok,7,"/Demo/testfile",""'
FS_WRITE_DATA='2021-05-18T00:50:00.005732Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_write_data,ok,12,"/Demo/atestfile.txt",""'
FS_CREATE_FILE='2021-05-18T00:50:00.00333Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_create_file,ok,12,"/Demo/atestfile.txt",""'

# This is the format from Qumulo's audit feature
QAUDIT='2021-05-18T21:41:55.861195Z qumulo-1 qumulo 192.168.240.1,"admin",smb2,fs_read_data,ok,6,"/test_qatime/testfile",""'

class TestMethods(TestCase):
    def test_list_directory_passes(self):
        result = qatime.pass_message(FS_LIST_DIRECTORY)
        self.assertTrue(result)

    def test_read_data_passes(self):
        result = qatime.pass_message(FS_READ_DATA)
        self.assertTrue(result)

    def test_write_data_passes(self):
        result = qatime.pass_message(FS_WRITE_DATA)
        self.assertTrue(result)

    def test_read_metadata_filtered(self):
        result = qatime.pass_message(FS_READ_METADATA)
        self.assertFalse(result)

    def test_write_metadata_filtered(self):
        result = qatime.pass_message(FS_WRITE_METADATA)
        self.assertFalse(result)

    def test_create_file_filtered(self):
        """no need to reset atime here as it's always initialized to create_time"""
        result = qatime.pass_message(FS_CREATE_FILE)
        self.assertFalse(result)

    def test_extract_keyvalue(self):
        target_file_path = '/Demo/'
        target_timestamp = '2021-05-18T00:02:22.357726Z'
        file_path, timestamp = qatime.extract_keyvalue(FS_LIST_DIRECTORY)
        self.assertEqual(target_file_path, file_path)
        self.assertEqual(target_timestamp, timestamp)

RC = RestClient(address='qumulo', port=8000)
RC.login(username=QLOGIN, password=QPASS)

def send_syslog_entry(data):
    syslogger = logging.getLogger('TestSysLogger')
    syslogger.setLevel(logging.DEBUG)
    handler = logging.handlers.SysLogHandler(address=('localhost', 514), facility=19)
    syslogger.addHandler(handler)
    syslogger.log(level=logging.DEBUG, msg=data)

def timestamp_to_epoch_utc(timestamp):
    fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
    epoch = int(time.mktime(time.strptime(timestamp, fmt)))
    return epoch

class TestIntegration(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Build test containers
        subprocess.check_call(['docker-compose', '-p', 'qatime_test', 'build'])
        # docker-compose up the test containers
        subprocess.check_output(['docker-compose', '-p', 'qatime_test', 'up', '-d'])

    @classmethod
    def tearDownClass(cls) -> None:
        # kill and remove the test containers
        # subprocess.check_output(['docker-compose', '-p', 'qatime_test', 'down'])
        # leave the containers up for now so we can look at their state in a test failure
        pass

    def test_atime_update_e2e(self):
        """make a testfile, drop a syslog entry that updates atime on the testfile, stat file and compare"""
        # create the test directory and a file in there
        RC.fs.create_directory(name=TEST_PATH.strip('/'), dir_path='/')
        RC.fs.create_file(name="testfile", dir_path=TEST_PATH)
        # drop a syslog entry on port 514 localhost that updates atime of the test file
        send_syslog_entry(QAUDIT)

        # This sleep is stupid, it's something to do with NFS caching, we shouldn't have to wait
        # attempting to disable NFS attribute and lookup caching on the client
        # on the plus side, a Redis entry that we fail to lookup on the fs stays put until the next cycle
        # I've observed it failing for several seconds repeatedly before the touch -a succeeds
        # it might need to wait long enough to catch the wait period in the atime setter thread??

        # The above might not be relevant now that I've disabled attribute and lookup caching on linux and in container
        # NOPE this still fails occasionally
        sleep(1)
        # stat the testfile, get atime, sleep and try again if we don't see it yet
        while True:
            try:
                atime = int(os.path.getatime('/mnt/qumulo/test_qatime/testfile')) # We don't need decimal seconds
                break
            except FileNotFoundError:
                print('File not found, waiting 1s for retry')
                sleep(1)


        # assert atime matches the previous timestamp
        self.assertEqual(timestamp_to_epoch_utc('2021-05-18T21:41:55.861195Z'), atime)
