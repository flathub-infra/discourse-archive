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
