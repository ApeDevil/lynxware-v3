#!/usr/bin/env python3
"""Generate vercel.json, public/sitemap.xml and public/robots.txt from tools/pages.txt and tools/downloads.txt."""
import json, os, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages = [u.strip() for u in open(os.path.join(ROOT, 'tools/pages.txt')) if u.strip()]
slugs = sorted(urllib.parse.urlparse(u).path.strip('/') for u in pages if urllib.parse.urlparse(u).path.strip('/'))
# Wix serves a separate mobile layout by user agent; so does this site (tablets get desktop, as on Wix).
# Case-sensitive on purpose: Vercel's header matching does not take an inline (?i) flag.
MOBILE = '.*(iPhone|iPod|Android.*Mobile|Windows Phone|BlackBerry|BB10|Opera Mini|Mobile Safari|IEMobile|webOS).*'
has = [{'type': 'header', 'key': 'user-agent', 'value': MOBILE}]
cfg = {
    '$schema': 'https://openapi.vercel.sh/vercel.json',
    'framework': None, 'buildCommand': None, 'installCommand': '', 'outputDirectory': 'public',
    'cleanUrls': True, 'trailingSlash': False,
    # Pages live in public/d (desktop) and public/m (mobile), not at the URL paths themselves:
    # Vercel serves a matching file before it looks at rewrites, so the user-agent rule would never run.
    'rewrites': [
        {'source': '/', 'has': has, 'destination': '/m/index'},
        {'source': f"/:page({'|'.join(slugs)})", 'has': has, 'destination': '/m/:page'},
        {'source': '/', 'destination': '/d/index'},
        {'source': f"/:page({'|'.join(slugs)})", 'destination': '/d/:page'},
    ],
    'redirects': [
        {'source': '/index', 'destination': '/', 'permanent': True},
        {'source': '/datenschutz', 'destination': '/privacy', 'permanent': True},
        # Not part of v3; these pages return with v4, so the redirect is temporary.
        {'source': '/:page(application|partnership)', 'destination': '/', 'permanent': False},
    ],
    'headers': [
        {'source': '/((?!assets/|fonts/|_files/).*)', 'headers': [
            {'key': 'Vary', 'value': 'User-Agent'},
            {'key': 'X-Content-Type-Options', 'value': 'nosniff'},
            {'key': 'Referrer-Policy', 'value': 'strict-origin-when-cross-origin'},
            {'key': 'X-Frame-Options', 'value': 'SAMEORIGIN'},
            {'key': 'Permissions-Policy', 'value': 'camera=(), microphone=(), geolocation=(), interest-cohort=()'},
        ]},
        {'source': '/(assets|fonts)/(.*)', 'headers': [{'key': 'Cache-Control', 'value': 'public, max-age=31536000, immutable'}]},
    ],
}
for u in open(os.path.join(ROOT, 'tools/downloads.txt')):
    u = u.strip()
    if not u:
        continue
    p = urllib.parse.urlparse(u)
    name = urllib.parse.parse_qs(p.query).get('dn', [os.path.basename(p.path)])[0]
    cfg['headers'].append({'source': p.path, 'headers': [{'key': 'Content-Disposition', 'value': f'attachment; filename="{name}"'}]})
json.dump(cfg, open(os.path.join(ROOT, 'vercel.json'), 'w'), indent=2)
with open(os.path.join(ROOT, 'public/sitemap.xml'), 'w') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for s in [''] + slugs + ['privacy']:
        f.write(f'<url><loc>https://www.lynxware.org/{s}</loc></url>\n'.replace('.org/<', '.org<') if not s else f'<url><loc>https://www.lynxware.org/{s}</loc></url>\n')
    f.write('</urlset>\n')
open(os.path.join(ROOT, 'public/robots.txt'), 'w').write('User-agent: *\nAllow: /\nDisallow: /m/\nDisallow: /d/\n\nSitemap: https://www.lynxware.org/sitemap.xml\n')
print('ok', slugs)
