import logging
import logging.handlers
import os
import subprocess
import time

import qatime

from datetime import datetime, timezone
from time import sleep
from typing import Sequence
from unittest import TestCase, main

from qatime_config import load_config
from qumulo.rest_client import RestClient

# Whether to tear down test resources or keep them (`env KEEP=1 ...`)
KEEP = bool(os.environ.get("KEEP"))
# docker-compose project name for tests
DC_PROJECT_NAME = "qatime_test"


# This is the format forwarded by Tommy's rsyslog config
FS_LIST_DIRECTORY = '2021-05-18T00:02:22.357726Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_list_directory,ok,6,"/Demo/",""'
FS_READ_METADATA = '2021-05-18T00:02:22.355392Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_read_metadata,ok,6,"/Demo/",""'
FS_READ_DATA = '2021-05-18T00:44:20.362001Z,qumulo-1,qumulo  192.168.240.129,"admin",api,fs_read_data,ok,7,"/Demo/testfile",""'
FS_WRITE_METADATA = '2021-05-18T00:44:20.395482Z,qumulo-1,qumulo  192.168.240.129,"0",nfs3,fs_write_metadata,ok,7,"/Demo/testfile",""'
FS_WRITE_DATA = '2021-05-18T00:50:00.005732Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_write_data,ok,12,"/Demo/atestfile.txt",""'
FS_CREATE_FILE = '2021-05-18T00:50:00.00333Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_create_file,ok,12,"/Demo/atestfile.txt",""'


class TestMethods(TestCase):
    def test_list_directory_passes(self) -> None:
        result = qatime.pass_message(FS_LIST_DIRECTORY)
        self.assertTrue(result)

    def test_read_data_passes(self) -> None:
        result = qatime.pass_message(FS_READ_DATA)
        self.assertTrue(result)

    def test_write_data_passes(self) -> None:
        result = qatime.pass_message(FS_WRITE_DATA)
        self.assertTrue(result)

    def test_read_metadata_filtered(self) -> None:
        result = qatime.pass_message(FS_READ_METADATA)
        self.assertFalse(result)

    def test_write_metadata_filtered(self) -> None:
        result = qatime.pass_message(FS_WRITE_METADATA)
        self.assertFalse(result)

    def test_create_file_filtered(self) -> None:
        # no need to reset atime here as it's always initialized to create_time
        result = qatime.pass_message(FS_CREATE_FILE)
        self.assertFalse(result)

    def test_extract_keyvalue(self) -> None:
        target_file_path = "/Demo/"
        target_timestamp = "2021-05-18T00:02:22.357726Z"
        file_path, timestamp = qatime.extract_keyvalue(FS_LIST_DIRECTORY)
        self.assertEqual(target_file_path, file_path)
        self.assertEqual(target_timestamp, timestamp)


class TestIntegration(TestCase):
    @staticmethod
    def dc_cmd(*args: str) -> Sequence[str]:
        return ["docker-compose", "--project-name", DC_PROJECT_NAME] + list(args)

    @classmethod
    def setUpClass(cls) -> None:
        subprocess.check_call(cls.dc_cmd("build"))
        subprocess.check_output(cls.dc_cmd("up", "-d"))

    def setUp(self) -> None:
        config = load_config()
        self.client = RestClient(address=config.rest.address, port=config.rest.port)
        self.client.login(username=config.rest.username, password=config.rest.password)
        self.remote_path = config.test.base_path
        self.test_folder = config.test.folder_name
        self.local_path = config.atime.nfs_mount

    @classmethod
    def tearDownClass(cls) -> None:
        if KEEP:
            print("Skipping docker-compose tear down")
        else:
            # kill test containers
            subprocess.check_output(cls.dc_cmd("down"))

    @staticmethod
    def send_syslog_entry(msg: str, host: str = "127.0.0.1", port: int = 514) -> None:
        syslogger = logging.getLogger("TestSysLogger")
        syslogger.setLevel(logging.DEBUG)
        handler = logging.handlers.SysLogHandler(address=(host, port), facility=19)
        syslogger.addHandler(handler)
        syslogger.log(level=logging.DEBUG, msg=msg)

    @staticmethod
    def epoch_to_datetime_utc(epoch: float) -> str:
        dt = datetime.fromtimestamp(epoch, timezone.utc)
        return f"{dt:%Y-%m-%dT%H:%M:%S.%fZ}"

    def test_atime_update_e2e(self) -> None:
        # create the test directory and a file via the REST API
        self.client.fs.create_directory(
            dir_path=self.remote_path, name=self.test_folder
        )
        dir_path = os.path.join(self.remote_path, self.test_folder, "")
        self.client.fs.create_file(dir_path=dir_path, name="testfile")
        remote_path = os.path.join(self.remote_path, self.test_folder, "testfile")

        # resolve those files to the locally mounted NFS location
        local_path = os.path.join(self.local_path, self.test_folder, "testfile")

        # drop a syslog entry on port 514 localhost. this should get picked up
        # by the container and update the atime of the test file
        expected_atime = "2021-05-18T21:41:55.861195Z"
        self.send_syslog_entry(
            f'{expected_atime} qumulo-1 qumulo 192.168.240.1,"admin",smb2,fs_read_data,ok,6,"{remote_path}",""'
        )

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
                atime = os.path.getatime(local_path)
                break
            except FileNotFoundError:
                print("File not found, waiting 1s for retry")
                sleep(1)

        if KEEP:
            print("Skipping test file removal")
        else:
            self.client.fs.delete(path=remote_path)
            self.client.fs.delete(path=dir_path)

        actual_atime = self.epoch_to_datetime_utc(atime)
        self.assertEqual(expected_atime, actual_atime)


if __name__ == "__main__":
    main()
