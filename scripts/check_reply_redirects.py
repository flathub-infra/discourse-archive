"""Check archive routing against a running nginx: python3 scripts/check_reply_redirects.py URL."""

import sys
import unittest
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


BASE_URL = sys.argv.pop(1).rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:18080"
CLIENT = urllib.request.build_opener(NoRedirect)


def request(path):
    try:
        return CLIENT.open(BASE_URL + path, timeout=10)
    except urllib.error.HTTPError as response:
        return response


class ReplyRedirectTests(unittest.TestCase):
    def test_search_console_examples(self):
        examples = [
            ("metainfo-files-in-upstream-or-flathub-repo", 6759, 8),
            ("wrong-origin-flathub-for-update", 2744, 3),
            ("flatpak-app-run-fail", 6499, 6),
            ("inactive-repo-ci-recent-failures", 12739, 2),
            ("first-time-flatpak-user-questions-on-flatpak-app-installation-and-update", 1926, 2),
            ("how-to-change-an-app-id", 124, 2),
        ]
        for slug, topic, post in examples:
            path = f"/t/{slug}/{topic}"
            with self.subTest(path=path):
                with request(f"{path}/{post}") as response:
                    self.assertEqual(response.status, 301)
                    self.assertEqual(response.headers["Location"], f"{path}#post_{post}")
                with request(path) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(f'id="post_{post}"', response.read().decode())

    def test_trailing_slash_and_query(self):
        path = "/t/metainfo-files-in-upstream-or-flathub-repo/6759"
        with request(path + "/8/?utm_source=test") as response:
            self.assertEqual(response.status, 301)
            self.assertEqual(response.headers["Location"], path + "#post_8")

    def test_continuation_pages(self):
        path = "/t/proposal-for-audio-plugins/399"
        for post, page in [(21, 2), (41, 3)]:
            with self.subTest(post=post):
                with request(f"{path}/{post}") as response:
                    self.assertEqual(response.status, 301)
                    self.assertEqual(response.headers["Location"], f"{path}/{page}.html#post_{post}")
                with request(f"{path}/{page}.html") as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(f'id="post_{post}"', response.read().decode())

    def test_missing_and_unrelated_paths(self):
        for path in [
            "/t/nonexistent-topic/999999999/2",
            "/t/metainfo-files-in-upstream-or-flathub-repo/6759/6",
            "/t/metainfo-files-in-upstream-or-flathub-repo/6759/999999999",
            "/t/metainfo-files-in-upstream-or-flathub-repo/6759/not-a-post",
            "/t/metainfo-files-in-upstream-or-flathub-repo/6759/8/extra",
            "/nonexistent-page",
        ]:
            with self.subTest(path=path), request(path) as response:
                self.assertEqual(response.status, 404)
                self.assertNotIn("Location", response.headers)


if __name__ == "__main__":
    unittest.main()
