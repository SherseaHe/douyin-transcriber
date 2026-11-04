import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import douyin_transcribe as cli


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'result'
        self.audio = self.root / 'audio.mp3'
        self.audio.write_bytes(b'original audio')
        self.calls = 0

    def recognize(self, **kwargs):
        self.calls += 1
        return 'request', {'result': {'text': f'transcript {self.calls}'}}

    def run_cli(self, source=None, extra=(), recognize=None):
        with patch('sys.argv', ['cli', str(source or self.audio), '--out-dir', str(self.out), '--json', *extra]), patch.object(cli.doubao_flash_asr, 'recognize_flash', side_effect=recognize or self.recognize), patch.object(cli, 'ffprobe_info', return_value={'duration_seconds': 1}), contextlib.redirect_stdout(io.StringIO()) as stdout:
            cli.main()
        return json.loads(stdout.getvalue())

    def test_cache_and_changed_input(self):
        self.assertEqual(self.run_cli()['status'], 'ok')
        self.assertEqual(self.run_cli()['status'], 'cached')
        self.audio.write_bytes(b'changed audio')
        self.assertEqual(self.run_cli()['status'], 'ok')
        other = self.root / 'other.mp3'
        other.write_bytes(b'changed audio')
        self.assertEqual(self.run_cli(other)['status'], 'ok')
        self.assertEqual(self.calls, 3)
        self.assertEqual(self.audio.read_bytes(), b'changed audio')

    def test_corrupt_output_and_language(self):
        self.run_cli()
        (self.out / 'transcript_raw.txt').write_text('corrupt')
        self.assertEqual(self.run_cli()['status'], 'ok')
        self.assertEqual(self.run_cli(extra=['--language', 'zh-CN'])['status'], 'ok')
        (self.out / 'summary.json').write_text('{broken')
        self.assertEqual(self.run_cli()['status'], 'ok')

    def test_failed_force_does_not_preserve_success(self):
        self.run_cli()
        with self.assertRaises(RuntimeError):
            self.run_cli(extra=['--force'], recognize=RuntimeError('ASR offline'))
        self.assertFalse((self.out / 'summary.json').exists())
        self.assertEqual(self.audio.read_bytes(), b'original audio')
        self.assertEqual(self.run_cli()['status'], 'ok')

    def test_real_ffmpeg_extraction(self):
        import wave
        video = self.root / 'clip.wav'
        with wave.open(str(video), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b'\x00\x00' * 16000)
        work = self.root / 'extract'
        work.mkdir()
        converted = cli.extract_audio(video, work)
        self.assertGreater(converted.stat().st_size, 0)
        self.assertGreater(cli.ffprobe_info(converted)['duration_seconds'], 0)
        self.assertTrue(video.exists())

    def test_concurrent_writer_rejected(self):
        self.out.mkdir()
        with (self.out / '.lock').open('a') as lock:
            cli.fcntl.flock(lock, cli.fcntl.LOCK_EX | cli.fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'Another transcription'):
                self.run_cli()
        self.assertEqual(self.calls, 0)

    def test_same_names_get_distinct_default_directories(self):
        a = self.root / 'a' / 'video.mp4'
        b = self.root / 'b' / 'video.mp4'
        for path in (a, b):
            path.parent.mkdir(); path.write_bytes(b'video')
        dirs = [cli.default_output_dir(str(p), {'input_identity': cli.input_identity(str(p), '')}) for p in (a, b)]
        self.assertNotEqual(*dirs)

    def test_fallback_isolation_and_cache_before_network(self):
        work_paths = []
        def download(source, work, cookies):
            work.mkdir(parents=True)
            work_paths.append(work)
            media = work / '123.mp3'
            media.write_bytes(b'new media')
            return media
        with patch.object(cli.douyin_resolver, 'resolve_douyin_url', side_effect=RuntimeError('blocked')) as resolver, patch.object(cli, 'download_video', side_effect=download):
            self.run_cli('https://www.douyin.com/video/123')
            self.assertEqual(self.run_cli('https://www.douyin.com/video/123')['status'], 'cached')
            self.assertEqual(resolver.call_count, 1)
            self.run_cli('https://www.douyin.com/video/456')
        self.assertNotEqual(*work_paths)
        self.assertTrue(all(not p.exists() for p in work_paths))
        self.assertEqual(self.calls, 2)

    def test_interrupted_download_never_publishes_partial(self):
        class Response(io.BytesIO):
            headers = {'Content-Length': '100'}
        dest = self.root / 'source.mp4'
        with patch.object(cli.urllib.request, 'urlopen', return_value=Response(b'partial')):
            with self.assertRaises(RuntimeError):
                cli.download_http('https://example.com/video', dest)
        self.assertFalse(dest.exists())
        self.assertFalse(dest.with_suffix('.mp4.part').exists())


if __name__ == '__main__':
    unittest.main()
