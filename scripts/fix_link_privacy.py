#!/usr/bin/env python3
"""Apply archive referrer privacy and mark external user-posted links."""

import argparse
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit


INTERNAL_HOST = "discourse.flathub.org"
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
REL_ATTRIBUTE = re.compile(
    r'''\srel(?=\s|=|/?>)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?''', re.IGNORECASE
)


def external_web_link(href):
    try:
        url = urlsplit(href.strip())
        return (url.scheme.lower() in {"http", "https"} or href.strip().startswith("//")) and bool(
            url.hostname and url.hostname.lower() != INTERNAL_HOST
        )
    except ValueError:
        return False


class LinkPrivacy(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.stack = []
        self.edits = []
        self.has_referrer = False
        self.head_end = None
        self.feed(source)

    def source_offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def replace_tag(self, replacement):
        start = self.source_offset()
        self.edits.append((start, start + len(self.get_starttag_text()), replacement))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        in_head = any(name == "head" for name, _ in self.stack)
        if tag == "meta" and in_head and (attrs.get("name") or "").lower() == "referrer":
            self.has_referrer = True
            self.replace_tag('<meta name="referrer" content="no-referrer">')
        if tag == "a":
            href = attrs.get("href") or ""
            external = external_web_link(href)
            in_post = any(post for _, post in self.stack)
            rel = list(dict.fromkeys((attrs.get("rel") or "").split()))
            required = []
            if external:
                required.append("noreferrer")
                if in_post:
                    required.extend(["nofollow", "ugc"])
            if (attrs.get("target") or "").lower() == "_blank":
                required.append("noopener")
            for token in required:
                if token not in [value.lower() for value in rel]:
                    rel.append(token)
            if required and rel != (attrs.get("rel") or "").split():
                original = self.get_starttag_text()
                attribute = f' rel="{escape(" ".join(rel), quote=True)}"'
                if "rel" in attrs:
                    replacement = REL_ATTRIBUTE.sub(lambda _: attribute, original, count=1)
                else:
                    end = original.rfind("/>") if original.endswith("/>") else len(original) - 1
                    replacement = original[:end] + attribute + original[end:]
                self.replace_tag(replacement)
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, "post-body" in (attrs.get("class") or "").split()))

    def handle_endtag(self, tag):
        if tag == "head":
            self.head_end = self.source_offset()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def repair(self):
        if not self.has_referrer and self.head_end is not None:
            self.edits.append((self.head_end, self.head_end,
                               '  <meta name="referrer" content="no-referrer">\n'))
        source = self.source
        for start, end, replacement in sorted(self.edits, reverse=True):
            source = source[:start] + replacement + source[end:]
        return source


def repair(source):
    return LinkPrivacy(source).repair()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if repairs are needed")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "output"
    changed = 0
    for path in sorted(root.rglob("*.html")):
        source = path.read_text()
        fixed = repair(source)
        if source != fixed:
            changed += 1
            if not args.check:
                path.write_text(fixed)
    print(f"{changed} pages {'need repair' if args.check else 'repaired'}")
    return int(args.check and changed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
