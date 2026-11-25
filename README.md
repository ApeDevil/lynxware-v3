# lynxware-v3 — www.lynxware.org (LYNXware v3 site, off Wix)

The LYNXware v3 website, moved from Wix to Vercel unchanged in look, content and URLs.
It is a temporary home until the v4 site (`ApeDevil/LYNXware`, v4.lynxware.org) replaces it.

## What it is

Plain static HTML, no build step, no server code:

| Path | What |
|------|------|
| `public/d/*.html` | Desktop pages, as Wix rendered them (scripts removed). |
| `public/m/*.html` | Mobile pages. Wix serves a separate mobile layout by user agent; `vercel.json` rewrites phones here and everything else to `d/` (a file at the URL path would win over the rewrite). |
| `public/privacy.html`, `public/impressum.svg` | Privacy policy and the Impressum card (same as v4). |
| `public/assets/` | Images, CSS and Work Sans fonts downloaded from Wix's CDN. |
| `public/fonts/` | Free substitutes (SIL OFL) for the Avenir/Futura faces Wix licenses only to Wix sites; `public/site.css` maps the family names. |
| `public/_files/archives/` | The software downloads, at their original Wix URLs (download file names via `Content-Disposition` in `vercel.json`). |
| `public/site.js` | Replaces the Wix runtime features used: mobile menu, back-to-top, click-to-load YouTube. |
| `tools/` | The extraction pipeline and tests. |

## Left out on purpose

The Wix pages "Join the team" (`/application`) and "Partnership" (`/partnership`), their menu entries and
buttons, and the contact form: they return with v4. Both URLs redirect (302) to `/`. See `REMOVED_IDS` in
`tools/convert.py`.

## Regenerate from Wix (only while Wix is still live)

```bash
tools/regenerate.sh
```

Captures every page in `tools/pages.txt` with Playwright (desktop 1440 px and iPhone), converts it with
`tools/convert.py`, and regenerates `vercel.json`, `sitemap.xml` and `robots.txt` (`tools/build_config.py`).
YouTube IDs of the Wix video players are in `tools/videos.txt`, the downloads in `tools/downloads.txt`.

## Test

```bash
python3 tools/serve.py public 8765 &                  # local stand-in for Vercel routing
node tools/test_functional.cjs http://127.0.0.1:8765  # menu, videos, downloads, links, redirects, 404
node tools/compare.cjs http://127.0.0.1:8765 OUT index diy …  # screenshots + external-request report
python3 tools/diff.py ORIG_SHOTS OUT DIFF_OUT          # pixel diff against the Wix screenshots
```
