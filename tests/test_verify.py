import tempfile
import unittest
from pathlib import Path

import verify


class VerifyToolDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.node = Path(self.temp.name) / 'node.exe'
        self.node.write_bytes(b'')

    def tearDown(self):
        self.temp.cleanup()

    def test_explicit_then_environment_then_path_then_standard_location(self):
        never = lambda name: None
        self.assertEqual(verify.find_node(str(self.node), {}, never, ()), str(self.node))
        self.assertEqual(verify.find_node(None, {'TRACELOFT_NODE': str(self.node)}, never, ()), str(self.node))
        self.assertEqual(verify.find_node(None, {}, lambda name: '/bin/node', ()), '/bin/node')
        self.assertEqual(verify.find_node(None, {}, never, (Path('missing'), self.node)), str(self.node))
        self.assertIsNone(verify.find_node(None, {}, never, (Path('missing'),)))

    def test_explicit_missing_node_is_an_error_not_a_fallback(self):
        with self.assertRaises(FileNotFoundError):
            verify.find_node('missing-node.exe', {}, lambda name: '/bin/node', ())

    def test_missing_git_reports_unknown_revision(self):
        self.assertEqual(verify.git_state(which=lambda name: None), (None, None))

    def test_missing_node_fails_verification_while_missing_ruff_is_optional(self):
        suites = verify.plan('python', None, False)
        self.assertIsNone(suites['javascript'][0])
        self.assertTrue(suites['javascript'][1])
        self.assertIsNone(suites['lint'][0])
        self.assertFalse(suites['lint'][1])
        ran = dict(status='ran', required=True, exit_code=0)
        self.assertFalse(verify.passed({'python': ran, 'javascript': dict(status='not_run', required=True, exit_code=None)}))
        self.assertTrue(verify.passed({'python': ran, 'lint': dict(status='not_run', required=False, exit_code=None)}))
        self.assertFalse(verify.passed({'python': ran, 'lint': dict(status='ran', required=False, exit_code=1)}))


if __name__ == '__main__':
    unittest.main()
