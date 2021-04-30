import redis

from unittest import TestCase

from datetime import datetime

# system under test
import qatime

TESTPATH='/'

# class TestQAtime(TestCase):
#     def test_iso_to_epoch(self):
#         iso_timestamp = '2021-04-20T17:17:11.40333Z'
#         iso_pattern = '%Y-%m-%dT%H:%M:%S.%fZ'
#         utc_time = datetime.strptime(iso_timestamp, iso_pattern)
#         epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
#         result = qatime.iso_to_epoch(iso_timestamp)
#
#         self.assertEqual(epoch_time, result)

class TestRedis(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = redis.Redis()

    def test_key_insert(self):
        key = "/root/"
        value = "2021-04-23T00:57:43.149082Z"
        self.R.set(key, value)
        result = self.R.get(key).decode("utf-8")
        self.assertEqual(result, value)

    def test_key_delete(self):
        key = "foo"
        value = "BAR"
        self.R.set(key, value)

