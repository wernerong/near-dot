"""A UTF-8 fixture must not disappear from Windows public-source scans."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PublicScanTests(unittest.TestCase):
    def test_unicode_source_is_scanned_and_suspected_values_are_not_printed(self):
        source = Path(__file__).resolve().parents[2] / 'scripts/scan-public.py'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / 'scripts').mkdir()
            (root / 'scripts/scan-public.py').write_bytes(source.read_bytes())
            subprocess.run(['git', 'init', '-q', str(root)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            fixture = root / 'synthetic-source.ts'
            url = 'https://chatgpt.com/c/' + 'synthetic-' + 'x' * 30
            fixture.write_text('const badge = "●";\nconst link = "' + url + '";\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(root / 'scripts/scan-public.py')], cwd=root,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('synthetic-source.ts:2: personal chat URL', result.stdout)
            self.assertNotIn(url, result.stdout + result.stderr)
            fixture.write_text('const badge = "●";\nconst link = "https://chatgpt.com/c/synthetic";\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(root / 'scripts/scan-public.py')], cwd=root,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
