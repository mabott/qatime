import qatime

from unittest import TestCase

# This is the format forwarded by Tommy's rsyslog config
FS_LIST_DIRECTORY='2021-05-18T00:02:22.357726Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_list_directory,ok,6,"/Demo/",""'
FS_READ_METADATA='2021-05-18T00:02:22.355392Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_read_metadata,ok,6,"/Demo/",""'
FS_READ_DATA='2021-05-18T00:44:20.362001Z,qumulo-1,qumulo  192.168.240.129,"admin",api,fs_read_data,ok,7,"/Demo/testfile",""'
FS_WRITE_METADATA='2021-05-18T00:44:20.395482Z,qumulo-1,qumulo  192.168.240.129,"0",nfs3,fs_write_metadata,ok,7,"/Demo/testfile",""'
FS_WRITE_DATA='2021-05-18T00:50:00.005732Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_write_data,ok,12,"/Demo/atestfile.txt",""'
FS_CREATE_FILE='2021-05-18T00:50:00.00333Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_create_file,ok,12,"/Demo/atestfile.txt",""'

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
