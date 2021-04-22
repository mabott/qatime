from unittest import TestCase

from datetime import datetime

# system under test
import qatime

TESTPATH='/'

class TestQAtime(TestCase):
    def test_iso_to_epoch(self):
        iso_timestamp = '2021-04-20T17:17:11.40333Z'
        iso_pattern = '%Y-%m-%dT%H:%M:%S.%fZ'
        utc_time = datetime.strptime(iso_timestamp, iso_pattern)
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        result = qatime.iso_to_epoch(iso_timestamp)

        self.assertEqual(epoch_time, result)

