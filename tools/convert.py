#!/usr/bin/env python3
"""Convert rendered Wix page snapshots into self-contained static HTML.

Input:  <capture>/{desktop,mobile}/<page>.html  (DOM after hydration, from tools/capture.js)
Output: public/<page>.html (desktop) and public/m/<page>.html (mobile), plus public/assets/**

What it does, deterministically:
- drops every <script>, Wix preload/preconnect hints and <noscript>
- downloads Wix-hosted media, stylesheets and fonts and rewrites their URLs to /assets/...
- drops fonts that Wix licenses only for Wix sites (public/site.css supplies free substitutes)
- rewrites links to www.lynxware.org to root-relative links
- replaces Wix video players with a click-to-load YouTube embed (no request to YouTube before consent)
- swaps the Wix-hosted HTML embed on /diy for a local copy
- adds /site.css and /site.js (mobile menu, forms, video consent)
Usage: convert.py <capture_dir> <out_public_dir> <videos.txt>
"""
import hashlib
import html
import os
import re
import sys
import urllib.parse
import urllib.request

CAP, OUT, VIDEOS = sys.argv[1], sys.argv[2], sys.argv[3]
ORIGIN = 'https://www.lynxware.org'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
LOCALIZE_HOSTS = ('static.wixstatic.com', 'static.parastorage.com', 'video.wixstatic.com',
                  'www-lynxware-org.filesusr.com', 'i.creativecommons.org')
# Monotype/Linotype faces Wix serves under its own licence are not ours to self-host: their
# @font-face rules are dropped, and public/site.css maps the same family names to free substitutes.
LICENSED_FONT = re.compile(r'helvetica|avenir|futura|din-next|proxima|brandon|museo|wfont', re.I)

cache = {}


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), r.headers.get('Content-Type', '')


EXT_BY_TYPE = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/gif': '.gif',
               'image/svg+xml': '.svg', 'text/css': '.css', 'font/woff2': '.woff2', 'font/woff': '.woff',
               'application/font-woff': '.woff', 'video/mp4': '.mp4', 'text/html': '.html',
               'font/ttf': '.ttf', 'application/x-font-ttf': '.ttf', 'image/x-icon': '.ico'}


def localize(url, base=None):
    """Download a Wix-hosted resource once and return its local URL; other URLs come back unchanged."""
    raw = html.unescape(url.strip().strip('\'"'))
    if raw.startswith('//'):
        raw = 'https:' + raw
    if base and not re.match(r'^[a-z]+:', raw):
        raw = urllib.parse.urljoin(base, raw)
    host = urllib.parse.urlparse(raw).netloc
    if host not in LOCALIZE_HOSTS:
        return url
    if raw in cache:
        return cache[raw]
    try:
        data, ctype = fetch(raw)
    except Exception as e:  # keep going; the validation step reports leftovers
        print('WARN fetch failed', raw, e, file=sys.stderr)
        cache[raw] = url
        return url
    ctype = ctype.split(';')[0].strip()
    path = urllib.parse.urlparse(raw).path
    ext = EXT_BY_TYPE.get(ctype) or (os.path.splitext(path)[1][:6] or '.bin')
    if ext == '.html':  # the DIY licence embed: serve its badge image locally too
        data = re.sub(r'src="([^"]+)"', lambda m: f'src="{localize(m.group(1))}"', data.decode('utf-8', 'replace')).encode()
    if ext == '.css' or ctype == 'text/css':
        data = process_css(data.decode('utf-8', 'replace'), raw).encode()
    name = hashlib.sha1(raw.encode()).hexdigest()[:16] + ext
    sub = {'.css': 'css', '.woff2': 'fonts', '.woff': 'fonts', '.ttf': 'fonts', '.mp4': 'video',
           '.html': 'embeds'}.get(ext, 'media')
    os.makedirs(os.path.join(OUT, 'assets', sub), exist_ok=True)
    with open(os.path.join(OUT, 'assets', sub, name), 'wb') as f:
        f.write(data)
    local = f'/assets/{sub}/{name}'
    cache[raw] = local
    return local


def substitute_font_face(block):
    fam = re.search(r'font-family:\s*([^;}]+)', block)
    return '' if fam and LICENSED_FONT.search(fam.group(1)) else None


def process_css(css, base=None):
    def face(m):
        sub = substitute_font_face(m.group(0))
        return sub if sub is not None else m.group(0)
    css = re.sub(r'@font-face\s*{[^}]*}', face, css)
    return re.sub(r'url\(\s*([^)]+?)\s*\)', lambda m: 'url(' + localize(m.group(1), base) + ')', css)


def process_srcset(val):
    parts = []
    for item in re.split(r',\s+', val.strip()):
        bits = item.strip().split()
        if bits:
            bits[0] = localize(bits[0])
            parts.append(' '.join(bits))
    return ', '.join(parts)


def internal_link(url):
    u = html.unescape(url)
    for pre in (ORIGIN, 'https://lynxware.org', 'http://www.lynxware.org'):
        if u == pre or u.startswith(pre + '/') or u.startswith(pre + '?') or u.startswith(pre + '#'):
            rest = u[len(pre):] or '/'
            return html.escape(rest, quote=True)
    return url


videos = {}
for line in open(VIDEOS):
    if line.strip():
        cid, url = line.split()
        m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url)
        videos[cid] = m.group(1)


def video_facade(m):
    cid = m.group(2)
    vid = videos.get(cid)
    if not vid:
        return m.group(0)
    return (m.group(1) +
            f'<div class="lx-video" data-youtube="{vid}">'
            '<button type="button" class="lx-video__play" aria-label="Play video">'
            '<svg viewBox="0 0 68 48" width="68" height="48" aria-hidden="true"><path d="M66.5 7.7A8.5 8.5 0 0 0 60.5 1.7C55.2.3 34 .3 34 .3S12.8.3 7.5 1.7a8.5 8.5 0 0 0-6 6C.1 13 .1 24 .1 24s0 11 1.4 16.3a8.5 8.5 0 0 0 6 6C12.8 47.7 34 47.7 34 47.7s21.2 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.9 35 67.9 24 67.9 24s0-11-1.4-16.3z" fill="#f00"/><path d="M45 24 27 14v20z" fill="#fff"/></svg></button>'
            '<p class="lx-video__note">Playing loads this video from YouTube (Google). '
            'By clicking you agree that data is sent to YouTube. '
            f'<a href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">Open on YouTube</a></p>'
            '</div></div>')


# Content that must differ from Wix. The former company no longer exists: the Impressum is the
# operator's personal one, the same card as v4.lynxware.org (public/impressum.svg).
IMPRESSUM_ALT = ('Stanislaw Kirpicnikow, Menninghauser Str. 29, 42859 Remscheid, Germany. '
                 'Email: s.kirpicnikow@gmx.de. Artist: ApeDevil.')


# Vercel Web Analytics (cookieless; served from this domain once enabled for the project).
ANALYTICS = ('<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};</script>'
             '<script defer src="/_vercel/insights/script.js"></script>')

# Announcement bar above the Wix header on every page.
V4_NOTICE = ('<div class="lx-notice" role="note">LYNXware v4 is coming in early 2027. '
             '<a href="https://v4.lynxware.org">Take a look at v4.lynxware.org</a></div>')

LEGAL_LINE = ('<nav class="lx-legal" aria-label="Legal"><a href="/impressum">Impressum</a>'
              '<span aria-hidden="true"> · </span><a href="/privacy">Privacy / Datenschutz</a></nav>')


# Left out of v3 on purpose (they return with v4): the "Join the team" and "Partnership" pages with
# their header buttons, mobile menu entries and homepage buttons, and the contact form (v3 sends no email).
# Also the footer "LYNXware Merchandise" button: lynxware.shop no longer exists.
REMOVED_IDS = ('comp-leq1klmh', 'comp-lcxrz3xk', 'comp-lmanctyl', 'comp-lmand3wl', 'comp-lrsyfamv', 'comp-lhnpiwym')


def remove_element(h, el_id):
    """Remove the element with this id, including everything nested in it."""
    m = re.search(r'<(\w+)\b[^>]*\bid="' + re.escape(el_id) + r'"', h)
    if not m:
        return h
    tag, depth, pos = m.group(1), 0, m.start()
    for t in re.finditer(r'<(/?)' + tag + r'\b[^>]*?(/?)>', h[pos:]):
        if t.group(2):
            continue
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return h[:pos] + h[pos + t.end():]
    raise ValueError(f'unbalanced <{tag}> for {el_id}')


def override_content(h):
    for el_id in REMOVED_IDS:
        h = remove_element(h, el_id)
    h = re.sub(r'<li\b[^>]*>(?:(?!</li>).)*href="https://www\.lynxware\.org/(?:application|partnership)"(?:(?!</li>).)*</li>', '', h, flags=re.S)
    # DIY: the "please visit the Join the Team page" paragraph and the spacer line above it.
    h = re.sub(r'(?:<p\b[^>]*>\s*<span[^>]*>​</span>\s*</p>\s*)?<p\b[^>]*>(?:(?!</p>).)*'
               r'If you are interested in being a part of the LYNXproject(?:(?!</p>).)*</p>', '', h, flags=re.S)
    return re.sub(r'<img\b[^>]*id="img_comp-lihrgu2l"[^>]*>',
                  lambda m: re.sub(r'\s(?:srcset|sizes|fetchpriority)="[^"]*"', '', m.group(0))
                  .replace(re.search(r'src="[^"]*"', m.group(0)).group(0), 'src="/impressum.svg"')
                  .replace(re.search(r'alt="[^"]*"', m.group(0)).group(0), f'alt="{IMPRESSUM_ALT}"')
                  .replace('object-fit:cover', 'object-fit:contain'), h)


def convert(src_html, mode):
    src_html = override_content(src_html)
    h = src_html
    h = re.sub(r'<script\b[^>]*>.*?</script>', '', h, flags=re.S | re.I)
    h = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', h, flags=re.S | re.I)
    h = re.sub(r'<link\b[^>]*rel="(?:preload|preconnect|dns-prefetch|modulepreload|prefetch)"[^>]*>', '', h, flags=re.I)
    h = re.sub(r'<link\b[^>]*rel="alternate"[^>]*>', '', h, flags=re.I)
    h = re.sub(r'<meta\b[^>]*name="(?:generator|skype_toolbar|format-detection)"[^>]*>', '', h, flags=re.I)
    # Wix's video players render their own placeholder; ours is consent-first.
    h = re.sub(r'(<div id="(comp-[a-z0-9]+)" class="VideoPlayer[^"]*"[^>]*>)\s*(?:<div [^>]*data-player-name="YouTube"[^>]*><div></div></div>)?\s*</div>', video_facade, h)
    h = re.sub(r'<style\b([^>]*)>(.*?)</style>', lambda m: f'<style{m.group(1)}>{process_css(m.group(2))}</style>', h, flags=re.S)
    h = re.sub(r'style="([^"]*url\([^"]*)"', lambda m: 'style="' + html.escape(process_css(html.unescape(m.group(1))), quote=True) + '"', h)
    h = re.sub(r'\b(src|poster|data-src|xlink:href)="([^"]+)"', lambda m: f'{m.group(1)}="{localize(m.group(2))}"', h)
    h = re.sub(r'\b(srcset|data-srcset)="([^"]+)"', lambda m: f'{m.group(1)}="{process_srcset(m.group(2))}"', h)
    h = re.sub(r'(<link\b[^>]*href=")([^"]+)(")', lambda m: m.group(1) + localize(m.group(2)) + m.group(3), h)
    h = re.sub(r'(<meta\b[^>]*content=")(https://static\.wixstatic\.com[^"]+)(")', lambda m: m.group(1) + ORIGIN + localize(m.group(2)) + m.group(3), h)
    h = re.sub(r'\bhref="([^"]+)"', lambda m: f'href="{internal_link(m.group(1))}"', h)
    h = re.sub(r'(<link\b[^>]*rel="canonical"[^>]*href=")/', lambda m: m.group(1) + ORIGIN + '/', h)
    h = h.replace('</head>', '<link rel="stylesheet" href="/site.css"><script src="/site.js" defer></script>' + ANALYTICS + '</head>', 1)
    h = re.sub(r'<html\b', f'<html data-lx-view="{mode}"', h, count=1)
    h = h.replace('</body>', LEGAL_LINE + '</body>', 1)
    h = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + V4_NOTICE, h, count=1)
    return h


for mode in ('desktop', 'mobile'):
    d = os.path.join(CAP, mode)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.html'):
            continue
        out_dir = os.path.join(OUT, 'd' if mode == 'desktop' else 'm')
        os.makedirs(out_dir, exist_ok=True)
        res = convert(open(os.path.join(d, fn), encoding='utf-8').read(), mode)
        open(os.path.join(out_dir, fn), 'w', encoding='utf-8').write(res)
        print(mode, fn, len(res))
print('assets', len(cache))
