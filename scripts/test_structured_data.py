"""Run with: python3 -m unittest discover -s scripts."""

from collections import defaultdict
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
        parent = next((item for _, item, _, _ in reversed(self.stack) if item is not None), None)
        props = attrs.get("itemprop", "").split()
        if parent is not None:
            parent["properties"].update(props)
        item = None
        if "itemscope" in attrs:
            item = {"type": attrs.get("itemtype", "").rsplit("/", 1)[-1],
                    "properties": set(), "values": defaultdict(str)}
            self.items.append(item)
        elif parent is not None:
            key = {"meta": "content", "link": "href", "a": "href", "img": "src",
                   "time": "datetime"}.get(tag)
            for prop in props:
                parent["values"][prop] += attrs.get(key, "") if key else ""
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, item, parent, props if item is None else []))

    def handle_data(self, data):
        owner = next((item for _, item, _, _ in reversed(self.stack) if item is not None), None)
        for tag, _, parent, props in self.stack:
            if parent is owner and owner is not None and tag not in {"a", "time"}:
                for prop in props:
                    owner["values"][prop] += data

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
                self.assertEqual(source, fixed, "Checked-in page needs repair")
                self.assertEqual(fixed, repair(fixed, path.relative_to(self.root)))
                items = Microdata(fixed).items
                topic = items[0]
                self.assertIn("url", topic["properties"])
                url = f"{ORIGIN}/{path.relative_to(self.root).as_posix()}"
                self.assertEqual(topic["values"]["url"], url)
                if path.name == "index.html":
                    self.assertEqual(topic["type"], "DiscussionForumPosting")
                    self.assertTrue({"headline", "author", "datePublished"} <= topic["properties"])
                    self.assertTrue({"text", "image", "video"} & topic["properties"])
                    self.assertTrue(topic["values"]["headline"].strip())
                else:
                    self.assertEqual(topic["type"], "CollectionPage")
                    self.assertIn("hasPart", topic["properties"])
                    self.assertNotIn("comment", topic["properties"])
                for item in items:
                    if item["type"] == "Person":
                        self.assertIn("name", item["properties"])
                        self.assertTrue(item["values"]["name"].strip())
                    if item["type"] == "Comment":
                        self.assertTrue({"author", "datePublished", "url"} <= item["properties"])
                        self.assertTrue({"text", "image", "video"} & item["properties"])
                        self.assertTrue(item["values"]["url"].startswith(url + "#post_"))
                    if item["type"] in {"DiscussionForumPosting", "Comment"}:
                        self.assertTrue(item["values"]["datePublished"].strip())
                        self.assertTrue(any(item["values"][prop].strip()
                                            for prop in ("text", "image", "video")))

    def test_author_values_are_scoped_and_nonempty(self):
        source = ('<article itemscope><h1 itemprop="name">Topic</h1>'
                  '<span itemprop="author" itemscope itemtype="http://schema.org/Person">'
                  '<span itemprop="name"> </span></span>'
                  '<span itemprop="author" itemscope itemtype="http://schema.org/Person">'
                  '<span itemprop="name">Ian &amp; Z</span></span></article>')
        people = [item for item in Microdata(source).items if item["type"] == "Person"]
        self.assertFalse(people[0]["values"]["name"].strip())
        self.assertEqual(people[1]["values"]["name"], "Ian & Z")

    def test_comment_text_does_not_satisfy_topic_content(self):
        source = ('<article itemscope itemtype="http://schema.org/DiscussionForumPosting">'
                  '<div itemprop="comment" itemscope itemtype="http://schema.org/Comment">'
                  '<div itemprop="text">Reply</div></div></article>')
        topic, comment = Microdata(source).items
        self.assertFalse(topic["values"]["text"].strip())
        self.assertEqual(comment["values"]["text"], "Reply")

    def test_image_only_comment_has_content_value(self):
        source = ('<div itemscope itemtype="http://schema.org/Comment">'
                  '<img src="/avatar.png"><div itemprop="text">'
                  '<img itemprop="image" src="/screenshot.png"></div></div>')
        comment = Microdata(source).items[0]
        self.assertFalse(comment["values"]["text"].strip())
        self.assertEqual(comment["values"]["image"], "/screenshot.png")

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
