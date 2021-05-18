import qatime

from unittest import TestCase

# This is the format forwarded by Tommy's rsyslog config
FS_LIST_DIRECTORY='2021-05-18T00:02:22.357726Z,qumulo-1,qumulo  192.168.240.129,"1000",nfs3,fs_list_directory,ok,6,"/Demo/",""'

class TestMethods(TestCase):
    def test_list_directory_passes(self):
        result = qatime.pass_message(FS_LIST_DIRECTORY)
        self.assertTrue(result)

    def test_extract_keyvalue(self):
        target_file_path = '/Demo/'
        target_timestamp = '2021-05-18T00:02:22.357726Z'
        file_path, timestamp = qatime.extract_keyvalue(FS_LIST_DIRECTORY)
        self.assertEqual(target_file_path, file_path)
        self.assertEqual(target_timestamp, timestamp)
