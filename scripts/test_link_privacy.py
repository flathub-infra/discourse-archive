from html.parser import HTMLParser
import unittest

from fix_link_privacy import repair


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


class LinkPrivacyTests(unittest.TestCase):
    def page(self, content):
        return '<html><head><title>Archive</title></head><body>' + content + '</body></html>'

    def test_external_post_links_preserve_attributes_and_destinations(self):
        source = self.page('''<div class="post-body"><blockquote><p>
<a href="https://example.org/?a=1&amp;b=2" target="_blank" rel='sponsored nofollow'>Link</a>
</p></blockquote><a href="//other.example/test">Other</a></div>''')
        fixed = repair(source)
        links = Links(fixed).links
        self.assertEqual(links[0]['href'], 'https://example.org/?a=1&b=2')
        self.assertEqual(set(links[0]['rel'].split()),
                         {'sponsored', 'nofollow', 'ugc', 'noreferrer', 'noopener'})
        self.assertEqual(set(links[1]['rel'].split()), {'nofollow', 'ugc', 'noreferrer'})
        self.assertIn('>Link</a>', fixed)

    def test_internal_navigation_and_non_web_links_unchanged(self):
        content = '<div class="post-body">' + ''.join(
            f'<a href="{url}">Link</a>' for url in [
                '/t/topic/123/index.html', '#post_2', 'mailto:test@example.org',
                'https://discourse.flathub.org/t/topic/123', '//discourse.flathub.org/',
            ]) + '</div><nav><a href="/page/2/index.html" rel="next">Next</a></nav>'
        self.assertIn(content, repair(self.page(content)))

    def test_external_editorial_link_is_not_marked_user_generated(self):
        source = self.page('<footer><a href="https://flathub.org">Flathub</a></footer>')
        self.assertEqual(Links(repair(source)).links[0]['rel'], 'noreferrer')

    def test_post_scope_does_not_leak(self):
        source = self.page('''<div class="post-body"><p><img src="a.png"><br>
<a href="https://a.example">A</a></p></div><a href="https://b.example">B</a>''')
        links = Links(repair(source)).links
        self.assertIn('ugc', links[0]['rel'])
        self.assertNotIn('ugc', links[1]['rel'])

    def test_referrer_policy_inserted_or_replaced_and_idempotent(self):
        for source in [self.page(''), self.page('').replace(
                '<title>', '<meta name="referrer" content="origin"><title>')]:
            fixed = repair(source)
            self.assertEqual(fixed.count('<meta name="referrer" content="no-referrer">'), 1)
            self.assertEqual(repair(fixed), fixed)

    def test_rel_is_merged_case_insensitively_and_idempotently(self):
        source = self.page('''<div class="post-body">
<a href="https://example.org" REL="NOFOLLOW UGC noreferrer">Link</a></div>''')
        self.assertEqual(Links(repair(source)).links[0]['rel'], 'NOFOLLOW UGC noreferrer')
        self.assertEqual(repair(repair(source)), repair(source))

    def test_empty_rel_and_new_tab_internal_links(self):
        source = self.page('''<div class="post-body"><a href="https://example.org" rel>Link</a>
<a href="/index.html" target="_blank">Home</a></div>''')
        links = Links(repair(source)).links
        self.assertEqual(set(links[0]['rel'].split()), {'nofollow', 'ugc', 'noreferrer'})
        self.assertEqual(links[1]['rel'], 'noopener')


if __name__ == '__main__':
    unittest.main()
