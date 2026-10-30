import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reel', Path(__file__).resolve().parents[1] / 'reel.py')
reel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reel)

class RenderServiceTest(unittest.TestCase):
    def test_agent_delegates_browser_render_with_auth_and_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / 'test-job'
            job.mkdir()
            with patch.object(reel, 'job_dir', return_value=job), patch.dict(os.environ, {
                'REEL_RENDER_SERVICE_URL': 'http://127.0.0.1:4321', 'REEL_RENDER_TOKEN': 'test-token'
            }), patch.object(reel.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"preview":"preview.mp4"}')) as request, patch.object(reel.subprocess, 'run') as spawn, patch('sys.stdout', new_callable=io.StringIO):
                reel.cmd_render(SimpleNamespace(job=str(job), preview=True))
                req = request.call_args.args[0]
                self.assertEqual(req.full_url, 'http://127.0.0.1:4321/api/jobs/test-job/render')
                self.assertEqual(req.get_header('Authorization'), 'Bearer test-token')
                self.assertEqual(json.loads(req.data), {'preview': True})
                spawn.assert_not_called()

if __name__ == '__main__':
    unittest.main()
