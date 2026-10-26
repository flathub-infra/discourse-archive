#!/usr/bin/env python3
"""Repair the exported Discourse templates without reformatting archived HTML."""

import argparse
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re


ORIGIN = "https://discourse.flathub.org"
TOPIC = '<article class="topic" itemscope itemtype="http://schema.org/DiscussionForumPosting">'
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class BodyImages(HTMLParser):
    """Locate body images so media-only posts also have structured content."""

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.lines = source.splitlines(keepends=True)
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line))
        self.stack = []
        self.images = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        in_body = any(body for _, body in self.stack)
        if tag == "img" and in_body and "itemprop" not in attrs:
            line, column = self.getpos()
            self.images.append(self.offsets[line - 1] + column + len("<img"))
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, "post-body" in attrs.get("class", "").split()))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)


def repair(source, relative_path):
    url = f"{ORIGIN}/{relative_path.as_posix()}"
    continuation = relative_path.name != "index.html"
    if continuation:
        source = source.replace(TOPIC, TOPIC.replace("DiscussionForumPosting", "CollectionPage"))
        source = source.replace('itemprop="comment"', 'itemprop="hasPart"')
    else:
        source = source.replace('class="topic-title" itemprop="name"',
                                'class="topic-title" itemprop="name headline"')
    article = re.search(r'<article class="topic"[^>]*>', source)
    if article and not source[article.end():].startswith('\n  <link itemprop="url"'):
        source = (source[:article.end()] + f'\n  <link itemprop="url" href="{url}">'
                  + source[article.end():])
    source = source.replace('<span class="user-link">',
                            '<span class="user-link" itemprop="name">')
    source = source.replace('itemprop="articleBody"', '')
    source = source.replace('\n         \n         >', '\n         >')
    source = re.sub(
        r'(<time itemprop="datePublished" datetime=")([^"]+)(")',
        lambda match: match[1] + datetime.fromisoformat(match[2]).isoformat() + match[3],
        source,
    )
    comment = re.compile(
        r'(<div class="post" id="(post_\d+)"\s+itemprop="(?:comment|hasPart)"'
        r'\s+itemscope itemtype="http://schema.org/Comment">)'
        r'(?!\n      <link itemprop="url")'
    )
    source = comment.sub(
        lambda match: match[1] + f'\n      <link itemprop="url" href="{url}#{match[2]}">',
        source,
    )
    for offset in reversed(BodyImages(source).images):
        source = source[:offset] + ' itemprop="image"' + source[offset:]
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if repairs are needed")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "output"
    changed = 0
    for path in sorted((root / "t").rglob("*.html")):
        source = path.read_text()
        fixed = repair(source, path.relative_to(root))
        if fixed != source:
            changed += 1
            if not args.check:
                path.write_text(fixed)
    print(f"{changed} topic pages {'need repair' if args.check else 'repaired'}")
    return int(args.check and changed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
