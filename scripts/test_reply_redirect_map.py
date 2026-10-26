"""Run with: python3 -m unittest discover -s scripts."""

from pathlib import Path
import tempfile
import unittest

from generate_reply_redirects import generate


class ReplyRedirectMapTests(unittest.TestCase):
    def test_actual_anchors_determine_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            topic = root / "t/example/123"
            topic.mkdir(parents=True)
            (topic / "index.html").write_text('<article id="post_1"></article>')
            (topic / "2.html").write_text('<article id="post_22"></article>')
            self.assertEqual(set(generate(root)), {
                '"/t/example/123/1" "/t/example/123#post_1";\n',
                '"/t/example/123/1/" "/t/example/123#post_1";\n',
                '"/t/example/123/22" "/t/example/123/2.html#post_22";\n',
                '"/t/example/123/22/" "/t/example/123/2.html#post_22";\n',
            })


if __name__ == "__main__":
    unittest.main()
