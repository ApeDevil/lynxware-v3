# lynxware-v3 — www.lynxware.org (LYNXware v3 site, off Wix)

The LYNXware v3 website, moved from Wix to Vercel unchanged in look, content and URLs.
It is a temporary home until the v4 site (`ApeDevil/LYNXware`, v4.lynxware.org) replaces it.

## What it is

Plain static HTML, no build step, plus one Vercel Function:

| Path | What |
|------|------|
| `public/*.html` | Desktop pages, as Wix rendered them (scripts removed). |
| `public/m/*.html` | Mobile pages. Wix serves a separate mobile layout by user agent; `vercel.json` rewrites phones to these. |
| `public/assets/` | Images, CSS and Work Sans fonts downloaded from Wix's CDN. |
| `public/fonts/` | Free substitutes (SIL OFL) for the Avenir/Futura faces Wix licenses only to Wix sites; `public/site.css` maps the family names. |
| `public/_files/archives/` | The software downloads, at their original Wix URLs (download file names via `Content-Disposition` in `vercel.json`). |
| `public/site.js` | Replaces the Wix runtime features used: mobile menu, back-to-top, forms, click-to-load YouTube. |
| `api/form.js` | `POST /api/form`: validates the Contact, Application and Partnership forms and emails them via Resend. Stores nothing. |
| `tools/` | The extraction pipeline and tests. |

## Configuration (Vercel project environment variables)

| Name | Value |
|------|-------|
| `RESEND_API_KEY` | Resend API key (sensitive). |
| `FORM_FROM` | Verified sender, e.g. `LYNXware Website <forms@lynxware.org>`. |
| `FORM_TO` | Recipient(s), comma-separated. |
| `ALLOWED_ORIGINS` | Optional extra origins allowed to post (the serving host is always allowed). |

Without them the forms answer "Form delivery is not configured yet" and point to the email address.

## Regenerate from Wix (only while Wix is still live)

```bash
tools/regenerate.sh
```

Captures every page in `tools/pages.txt` with Playwright (desktop 1440 px and iPhone), converts it with
`tools/convert.py`, and regenerates `vercel.json`, `sitemap.xml` and `robots.txt` (`tools/build_config.py`).
YouTube IDs of the Wix video players are in `tools/videos.txt`, the downloads in `tools/downloads.txt`.

## Test

```bash
node --test tests/form.test.mjs                       # form handler, Resend mocked
python3 tools/serve.py public 8765 &                  # local stand-in for Vercel routing
node tools/test_functional.cjs http://127.0.0.1:8765  # menu, forms, videos, downloads, links, 404
node tools/compare.cjs http://127.0.0.1:8765 OUT index diy …  # screenshots + external-request report
python3 tools/diff.py ORIG_SHOTS OUT DIFF_OUT          # pixel diff against the Wix screenshots
```
