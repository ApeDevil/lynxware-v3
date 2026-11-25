#!/usr/bin/env python3
"""Generate vercel.json, public/sitemap.xml and public/robots.txt from tools/pages.txt and tools/downloads.txt."""
import json, os, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages = [u.strip() for u in open(os.path.join(ROOT, 'tools/pages.txt')) if u.strip()]
slugs = sorted(urllib.parse.urlparse(u).path.strip('/') for u in pages if urllib.parse.urlparse(u).path.strip('/'))
# Wix serves a separate mobile layout by user agent; so does this site (tablets get desktop, as on Wix).
MOBILE = '(?i).*(iphone|ipod|android.*mobile|windows phone|blackberry|bb10|opera mini|mobile safari|iemobile|webos).*'
has = [{'type': 'header', 'key': 'user-agent', 'value': MOBILE}]
cfg = {
    '$schema': 'https://openapi.vercel.sh/vercel.json',
    'framework': None, 'buildCommand': None, 'installCommand': '', 'outputDirectory': 'public',
    'cleanUrls': True, 'trailingSlash': False,
    'rewrites': [
        {'source': '/', 'has': has, 'destination': '/m/index.html'},
        {'source': f"/:page({'|'.join(slugs)})", 'has': has, 'destination': '/m/:page.html'},
    ],
    'redirects': [
        {'source': '/index', 'destination': '/', 'permanent': True},
        {'source': '/datenschutz', 'destination': '/privacy', 'permanent': True},
        {'source': '/m/:path*', 'destination': '/:path*', 'permanent': False, 'missing': has},
    ],
    'headers': [
        {'source': '/((?!assets/|fonts/|_files/|api/).*)', 'headers': [
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
open(os.path.join(ROOT, 'public/robots.txt'), 'w').write('User-agent: *\nAllow: /\nDisallow: /m/\n\nSitemap: https://www.lynxware.org/sitemap.xml\n')
print('ok', slugs)
