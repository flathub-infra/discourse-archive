"""Run with: python3 -m unittest discover -s scripts."""

from html.parser import HTMLParser
from pathlib import Path
import unittest

from fix_structured_data import ORIGIN, VOID_ELEMENTS, repair


class Microdata(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.stack = []
        self.items = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        parent = next((item for _, item in reversed(self.stack) if item is not None), None)
        props = attrs.get("itemprop", "").split()
        if parent is not None:
            parent["properties"].update(props)
        item = None
        if "itemscope" in attrs:
            item = {"type": attrs.get("itemtype", "").rsplit("/", 1)[-1], "properties": set()}
            self.items.append(item)
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, item))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)


class StructuredDataTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1] / "output"

    def test_archive_scopes_and_idempotence(self):
        pages = list((self.root / "t").rglob("*.html"))
        self.assertTrue(pages)
        for path in pages:
            with self.subTest(path=path):
                source = path.read_text()
                fixed = repair(source, path.relative_to(self.root))
                self.assertEqual(fixed, repair(fixed, path.relative_to(self.root)))
                items = Microdata(fixed).items
                topic = items[0]
                self.assertIn("url", topic["properties"])
                if path.name == "index.html":
                    self.assertEqual(topic["type"], "DiscussionForumPosting")
                    self.assertTrue({"headline", "author", "datePublished"} <= topic["properties"])
                    self.assertTrue({"text", "image", "video"} & topic["properties"])
                else:
                    self.assertEqual(topic["type"], "CollectionPage")
                    self.assertIn("hasPart", topic["properties"])
                    self.assertNotIn("comment", topic["properties"])
                for item in items:
                    if item["type"] == "Person":
                        self.assertIn("name", item["properties"])
                    if item["type"] == "Comment":
                        self.assertTrue({"author", "datePublished", "url"} <= item["properties"])
                        self.assertTrue({"text", "image", "video"} & item["properties"])

    def test_media_only_content_gets_image_property(self):
        source = '<div class="post-body cooked" itemprop="text"><p><img src="/a.png"></p></div>'
        fixed = repair(source, Path("t/example/1/index.html"))
        self.assertIn('<img itemprop="image" src="/a.png">', fixed)

    def test_avatar_is_not_post_image(self):
        source = '<div class="post-avatar"><img src="/avatar.png"></div>'
        self.assertEqual(source, repair(source, Path("t/example/1/index.html")))

    def test_topic_and_comment_urls(self):
        path = Path("t/need-help-with-libimobiledevice/11050/2.html")
        fixed = repair((self.root / path).read_text(), path)
        self.assertIn(f'href="{ORIGIN}/{path}"', fixed)
        self.assertIn(f'href="{ORIGIN}/{path}#post_21"', fixed)


if __name__ == "__main__":
    unittest.main()
