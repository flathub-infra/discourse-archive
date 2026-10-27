# Archive structured data

The archive is checked in as static HTML; the original export templates are not
part of this repository. After replacing or regenerating `output/`, run:

```sh
python3 scripts/fix_structured_data.py
python3 -m unittest discover -s scripts
python3 scripts/fix_structured_data.py --check
```

The repair preserves the page content and formatting while adding author names,
topic headlines, absolute topic/comment URLs, ISO 8601 publication dates, and
image properties for post images (including image-only posts). Continuation
pages use `CollectionPage` with `hasPart` comments rather than claiming to be
complete `DiscussionForumPosting` objects without an original post.

Author profile URLs are intentionally omitted: the export has display names but
no profile pages or reliable username-to-profile mapping. Google's optional
author URL warnings may remain; do not fabricate URLs to silence them.

After deployment, test representative first and continuation pages using Google's
Rich Results Test, then request validation in Search Console. Existing reports
will not update until Google recrawls the changed pages.

## Reply URL redirects

The Docker build generates an nginx map from the archived `post_<number>`
anchors. Legacy Discourse reply URLs redirect permanently to the page containing
the reply, including continuation pages. Missing topics and replies remain 404s.
Query strings are discarded on these redirects.

To check the production image locally (replace `docker` with `podman` if needed):

```sh
docker build -t discourse-archive:test .
docker run --detach --rm --name archive-test -p 127.0.0.1:18080:8080 discourse-archive:test
docker exec archive-test nginx -t
python3 scripts/check_reply_redirects.py http://127.0.0.1:18080
docker stop archive-test
```

The map generator is covered by the standard unittest discovery command above;
the HTTP checks run separately because they need a running nginx.

## Color theme

The shared archive stylesheet uses Flathub's palette and follows the system
color scheme by default, including without JavaScript. The header's System /
Light / Dark chooser is added by `output/assets/js/archive.js` and saves its
override in local storage. Returning to System follows OS changes automatically.
The styles use modern CSS `light-dark()` and `oklch()` colors.

Run the theme preference tests with:

```sh
node --test scripts/test_theme.cjs
```
