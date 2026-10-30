"""Pipeline regression checks; no model calls, transcription service or renders."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reel', Path(__file__).with_name('reel.py'))
reel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reel)

class CreationTests(unittest.TestCase):
    def job(self, root, features):
        job = Path(root) / 'job'
        (job / 'input').mkdir(parents=True)
        (job / 'public').mkdir()
        (job / 'input/source.mp4').touch()
        for name, data in {
            'job.json': {}, 'ui.json': {'features': features},
            'style.json': {'canvas': {'width': 1920, 'height': 1080, 'fps': 30}, 'captions': {'enabled': True}},
            'transcript.json': {'duration': 10, 'words': [
                {'i': 0, 'word': 'Hello', 'start': 1, 'end': 2},
                {'i': 1, 'word': 'um', 'start': 4, 'end': 4.5},
                {'i': 2, 'word': 'world.', 'start': 6, 'end': 7}]},
        }.items(): reel.wj(job / name, data)
        return job

    def test_rough_cut_off_keeps_fillers_pauses_and_entire_source(self):
        with tempfile.TemporaryDirectory() as root:
            job = self.job(root, {'roughCut': False})
            with patch.object(reel, 'run') as run:
                reel.cmd_cut(SimpleNamespace(job=str(job), gap=.4, pad=.12))
            edl = reel.rj(job / 'edl.json')
            self.assertEqual(edl['duration'], 10)
            self.assertEqual(edl['segments'][0]['src_start'], 0)
            self.assertEqual(edl['segments'][0]['src_end'], 10)
            self.assertEqual(len(reel.rj(job / 'transcript-cut.json')['words']), 3)
            self.assertIn('scale=1920:1080', (job / 'cut-filter.txt').read_text())
            run.assert_called_once()

    def test_explicit_word_removal_still_applies_with_rough_cut_off(self):
        with tempfile.TemporaryDirectory() as root:
            job = self.job(root, {'roughCut': False})
            reel.wj(job / 'cuts.json', [{'from': 2, 'to': 2, 'reason': 'user request'}])
            with patch.object(reel, 'run'):
                reel.cmd_cut(SimpleNamespace(job=str(job), gap=.4, pad=.12))
            self.assertEqual([w['word'] for w in reel.rj(job / 'transcript-cut.json')['words']], ['Hello', 'um'])

    def test_disabled_features_are_removed_before_validation_and_render(self):
        with tempfile.TemporaryDirectory() as root:
            job = self.job(root, dict(subtitles=False, music=False, sfx=False, motionGraphics=False))
            reel.wj(job / 'transcript-cut.json', reel.rj(job / 'transcript.json'))
            reel.wj(job / 'beat-plan.json', {'music': {'file': 'missing.mp3'}, 'beats': [{'layout': 'fullscreen', 'graphic': {'type': 'text'}, 'zoom': 1.3, 'transition': 'whip', 'sfx': [{'file': 'missing.wav'}]}]})
            with patch.dict('os.environ', {}, clear=True), patch.object(reel, 'validate_plan', return_value=[]), patch.object(reel.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
                reel.cmd_render(SimpleNamespace(job=str(job), preview=True))
            props = reel.rj(job / 'props.json')
            self.assertIsNone(props['music'])
            self.assertFalse(props['style']['captions']['enabled'])
            self.assertEqual(props['beats'][0], {'layout': 'talking_head', 'zoom': 1, 'transition': 'cut', 'sfx': []})

    def test_ingest_uses_job_format_without_changing_saved_style(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            style_dir = root / 'style'
            style_dir.mkdir()
            source = root / 'source.mp4'; source.touch()
            job = root / 'jobs/example'; job.mkdir(parents=True)
            reel.wj(job / 'ui.json', {'aspectRatio': '16:9'})
            style = {'canvas': {'width': 1080, 'height': 1920, 'fps': 30}}
            with patch.object(reel, 'ROOT', root), patch.object(reel, 'find_style', return_value=style_dir), patch.object(reel, 'load_style', return_value=style), patch.object(reel, 'probe', return_value={'width': 1920, 'has_audio': True}):
                reel.cmd_ingest(SimpleNamespace(video=str(source), style='style', id='example'))
            self.assertEqual(reel.rj(job / 'style.json')['canvas'], {'width':1920,'height':1080,'fps':30})
            self.assertFalse((style_dir / 'style.json').exists())

if __name__ == '__main__': unittest.main()
