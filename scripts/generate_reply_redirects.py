"""Generate an nginx map from the actual archived reply anchors."""

from html.parser import HTMLParser
from pathlib import Path
import re
import sys


class PostAnchors(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.posts = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        anchor = dict(attrs).get("id", "")
        if re.fullmatch(r"post_[0-9]+", anchor):
            self.posts.append(anchor.removeprefix("post_"))


def generate(root):
    for page in sorted((root / "t").glob("*/*/*.html")):
        relative = page.relative_to(root).as_posix()
        # Only accept topic paths that can safely appear literally in nginx config.
        if not re.fullmatch(r"t/[a-zA-Z0-9_-]+/[0-9]+/(index|[0-9]+)\.html", relative):
            raise ValueError(f"Unexpected topic path: {relative}")
        topic = "/" + page.parent.relative_to(root).as_posix()
        destination = topic if page.name == "index.html" else "/" + relative
        for post in PostAnchors(page.read_text(encoding="utf-8")).posts:
            for suffix in ["", "/"]:
                yield f'"{topic}/{post}{suffix}" "{destination}#post_{post}";\n'


if __name__ == "__main__":
    root, destination = map(Path, sys.argv[1:])
    destination.write_text("".join(generate(root)), encoding="utf-8")
