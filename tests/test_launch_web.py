"""Service identity compatibility prevents a second server during a rename."""
import io
import unittest
from unittest.mock import patch

from launch_web import ready


class LauncherIdentityTests(unittest.TestCase):
    def test_recognizes_current_and_already_running_legacy_service(self):
        for name in ('TraceLoft', 'GolfData'):
            with self.subTest(name=name), patch('launch_web.urllib.request.urlopen',
                    return_value=io.BytesIO(('{"app":"' + name + '"}').encode())):
                self.assertTrue(ready(8765))

    def test_does_not_recognize_other_services_or_invalid_responses(self):
        for body in (b'{"app":"Other"}', b'{}', b'not json'):
            with self.subTest(body=body), patch('launch_web.urllib.request.urlopen',
                    return_value=io.BytesIO(body)):
                self.assertFalse(ready(8765))

    def test_unavailable_service_is_not_ready(self):
        with patch('launch_web.urllib.request.urlopen', side_effect=OSError):
            self.assertFalse(ready(8765))
