import tempfile
import unittest
from pathlib import Path
import server
import access

class AccessTest(unittest.TestCase):
    def test_password_session_logout(self):
        old=server.DB
        with tempfile.TemporaryDirectory() as tmp:
            server.DB=Path(tmp)/'access.db'
            try:
                access.add('teacher','testing123','teacher')
                with self.assertRaises(ValueError):access.login('teacher','wrong')
                token,u=access.login('teacher','testing123')
                cookie='teaching_session='+token
                self.assertEqual(access.user(cookie)['role'],'teacher')
                access.logout(cookie)
                self.assertIsNone(access.user(cookie))
            finally:server.DB=old
