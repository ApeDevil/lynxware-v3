# LYNXware v3: Wix → Vercel migration report

Status: **live on https://www.lynxware.org from Vercel (Hobby) since 2026-11-25, validated on the production domain.** **Migration complete (2026-11-25):** Wix disconnected and its plan cancelled, Vercel team upgraded to Pro. Decided by Stas: no export of Wix form submissions or contacts, and no email check (the Namecheap forwarding records were left as they were).

DNS switched at Namecheap on 2026-11-25: `A @` 185.230.63.107/.171/.186 → `216.150.1.1`; `CNAME www` `cdn1.wixdns.net` → `3cf2b555e36ab3a7.vercel-dns-016.com`. MX (email forwarding), SPF TXT and the `v4` CNAME verified unchanged. Let's Encrypt certificate for www.lynxware.org issued (valid to 2027-02-23); `lynxware.org/*` redirects 308 to `https://www.lynxware.org/*`. On the production domain: both layouts by device, the browser checks, 25/25 internal links, 11/11 downloads byte-identical, no external requests or errors.

## Scope change (2026-11-25, decided by Stas)

v3 is kept as simple as possible: the "Join the team" and "Partnership" pages, their menu entries and homepage buttons, and the contact form were dropped (they return with v4); `/application` and `/partnership` redirect (302) to `/`. With no forms left, the site has no server code and no Resend; the form function, its tests and the form section of the privacy policy were removed. Sections below that mention forms or Resend describe the earlier state. The /diy sentence pointing to the Join the Team page was removed as well.

## 1. Infrastructure found

| Concern | Where it lives | Change needed |
|---|---|---|
| Domain registration | **Namecheap** (registered 2023-04-12, expires 2027-04-12, transfer-locked) | None. No transfer needed. |
| DNS | **Namecheap BasicDNS** (`dns1/dns2.registrar-servers.com`) | Two records at cutover (section 6). |
| Email | **Namecheap email forwarding** (MX `eforward1-5.registrar-servers.com`, SPF TXT) | None. Untouched by the move. |
| Website hosting | **Wix** (apex A → 185.230.63.107/.171/.186, `www` CNAME → `cdn1.wixdns.net`) | Replaced by Vercel. |
| v4 site | `v4.lynxware.org` CNAME → Vercel (project `lynxware`, repo `ApeDevil/LYNXware`) | None. Not touched. |
| Email sending | Resend, already used by the Vercel project `densho` | Reused for the forms. |

## 2. Architecture and extraction strategy

- **Extraction:** Playwright renders each page as Wix serves it (desktop 1440 px and iPhone UA), scrolls to trigger lazy loading, and saves the hydrated DOM. `tools/convert.py` then deterministically strips every Wix script, downloads media/CSS/fonts, rewrites links and emits static HTML. Nothing was retyped by hand.
  - SingleFile would inline everything into one huge file per page (hard to maintain, no shared assets); HTTrack/wget only see the server HTML, missing the hydrated state and lazy media; Wix has no code/site export for Editor sites. The Playwright + converter route gave identical layouts with shared, cacheable assets.
- **Site:** plain static HTML (no framework, no build), one small script (`public/site.js`) replacing the Wix runtime parts used: mobile menu, back-to-top, forms, video players.
- **Mobile:** Wix serves a separate mobile layout by user agent. `vercel.json` does the same with a header-matched rewrite to `public/m/*` (no JavaScript), tablets get desktop as on Wix.
- **Forms:** `api/form.js` (Vercel Function, no dependencies) validates server-side (form name, email, URLs, field count/size, same-origin), traps spam with a honeypot + minimum fill time + per-IP rate limit (replacing Wix's reCAPTCHA, so no Google script), sends via Resend with the visitor as Reply-To, stores nothing.
- **Videos:** the five YouTube players show a click-to-load placeholder; nothing is requested from YouTube before the click, then `youtube-nocookie.com` is embedded (GDPR/TTDSG-friendly).
- **Downloads:** the 11 ZIPs (≈150 MB) are served statically at their **original URLs** (`/_files/archives/…`), with the original file names via `Content-Disposition`. GitHub Releases weren't needed: every file is < 50 MB.
- **Fonts:** Work Sans (OFL) self-hosted. Helvetica/Avenir/Futura are Monotype fonts Wix licenses only for Wix-hosted sites, so they were not copied: Helvetica uses the visitor's Helvetica/Arial (Wix's own fallback), Avenir → Nunito Sans, Futura → Jost (both OFL, self-hosted).
- **URLs:** all 8 paths preserved (`/`, `/diy`, `/tutorials`, `/downloads`, `/contact`, `/application`, `/partnership`, `/impressum`), plus sitemap, robots, canonical and Open Graph tags, favicon and a 404 page.

## 3. Validation (automated, against a local copy with Vercel's routing)

Pixel diff against the Wix screenshots (`tools/compare.cjs` + `tools/diff.py`; differing pixels with a 40/255 threshold):

| Page | Desktop height Wix → new | Desktop diff | Mobile height Wix → new | Mobile diff |
|---|---|---|---|---|
| Home | 6495 → 6495 | 1.18 % | 3521 → 3521 | 3.16 % |
| DIY | 12683 → 12683 | 1.23 % | 8601 → 8601 | 2.56 % |
| Tutorials | 1970 → 1970 | 0.76 % | 1121 → 1121 | 4.51 % |
| Downloads | 2062 → 2062 | 0.69 % | 2195 → 2195 | 1.98 % |
| Contact | 1574 → 1574 | 0.71 % | 1887 → 1887 | 1.17 % |
| Application | 3364 → 3364 | 1.66 % | 3326 → 3205 | 13.84 % ¹ |
| Partnership | 1688 → 1688 | 1.49 % | 1757 → 1756 | 3.76 % |
| Impressum | 925 → 925 | 0.45 % | 866 → 866 | 1.39 % |
| Home @1280 / @1920 px | identical heights | 1.33 % / 0.89 % | | |

Remaining differences are glyph shapes from the font substitution (and video placeholders where Wix showed an empty player). ¹ The reCAPTCHA box is gone, so the content below it moves up ~120 px.

Functional tests (`tools/test_functional.cjs`), all **PASS**: mobile/desktop routing by user agent; mobile menu opens, lists every page, closes; no YouTube request before consent, then youtube-nocookie embed; Contact, Application and Partnership forms post every field and show their Wix success message; empty required fields block submit; all 11 downloads respond; every internal link on all 16 page variants resolves; unknown paths give 404.

Form handler tests (`tests/form.test.mjs`, Resend mocked), all **PASS** (6/6): delivery with Reply-To and HTML escaping; honeypot and too-fast submits silently dropped; invalid email/unknown form/bad URL/too many fields rejected; foreign origin and non-POST refused; missing configuration answers 503; rate limit after 5 submits.

Independence from Wix: with every non-local request blocked, **no page requested anything external** (no `wixstatic`, `parastorage`, `wix.com`, Sentry, analytics or fonts; the Creative Commons badge of the DIY licence notice is served locally) and no resource failed. Every page is 53 px taller for the legal line under the footer.

### Live deployment (https://lynxware-v3.vercel.app, commit 5f3598f)

- Phones get the mobile layout and everything else the desktop layout, on every page (desktop pages live in `public/d`, because Vercel serves a matching file before it evaluates rewrites).
- The same browser checks pass live: menu, click-to-load videos, all three forms (posting intercepted), required fields, 404. All 25 internal links answer 2xx/3xx; all 11 downloads are byte-identical to Wix (SHA-256) with their original file names.
- No external requests, console errors or failed resources on any page; the visual diff equals the local build.
- `/api/form` answers "Form delivery is not configured yet" until `RESEND_API_KEY`, `FORM_FROM` and `FORM_TO` are set.

## 4. Remaining discrepancies and limitations

- **Intended content change:** the former company no longer exists, so the Impressum image (company, register and VAT data) is replaced by the personal Impressum of v4.lynxware.org (`public/impressum.svg`, applied by `tools/convert.py`). The old image was removed from the site and the media archive.
- Fonts differ slightly for visitors without Helvetica/Avenir/Futura installed (see above). Apple devices have Helvetica and Avenir, so they see the original faces.
- The Wix entrance animations are not reproduced; the pages show their final state immediately.
- No reCAPTCHA (replaced by server-side spam protection).
- **Privacy policy added** at `/privacy` (`/datenschutz` redirects), linked with the Impressum from a line under the footer of every page. The Wix site had none. It is based on the v4 draft, adapted to v3, and shows a "Draft: awaiting legal review" notice until the open points below are confirmed.
- No cookie banner appeared on the Wix site in any capture; with Wix's tracking removed and YouTube behind a click, no consent banner is needed.

### Privacy policy: open points for Stas (marked `CONFIRM` in `public/privacy.html`)

Verified from the providers' own pages: Vercel is certified under the EU-U.S. Data Privacy Framework; Vercel keeps function runtime logs about one hour on Hobby; Resend keeps emails and logs 30 days on its free plan, stores data in the USA, and covers transfers with the DPF and Standard Contractual Clauses; YouTube's privacy-enhanced mode is provided by Google Ireland.

1. Data processing agreement with Vercel (Art. 28 GDPR): Vercel's DPA is offered for Pro/Enterprise; confirm what applies on Hobby, and accept the DPA after the Pro upgrade. Vercel's infrastructure request-log retention is not published for Hobby.
2. Supervisory authority: LDI NRW, derived from the Remscheid address.
3. Legal review of the whole text, then remove the draft notice.
5. Vercel Web Analytics (added 2026-11-25, cookieless, script from the site's own domain): legal review of the legitimate-interest basis and of the conclusion that no § 25 TDDDG consent is needed.
4. The footer still links "LYNXware Merchandise" (lynxware.shop); check that the shop still exists now that the company is gone.

## 5. Recurring costs

| Item | Before | After |
|---|---|---|
| Wix Premium plan | yes | **cancelled after cutover** |
| Vercel | existing team (Hobby; LYNXware is a personal, non-commercial project) | Pro, $20/month per member, upgraded once Wix is cancelled (decided by Stas) |
| Domain (Namecheap) | annual renewal | unchanged |
| GitHub | private repo | $0 |

## 6. Cutover checklist (do not start before the preview is approved)

Before:
1. Export from Wix (section 7). 2. In Namecheap, lower TTL of the `@` A records and the `www` CNAME to 5 min, a day ahead.

Switch:
3. Vercel → project `lynxware-v3` → Settings → Domains: add `www.lynxware.org` (primary) and `lynxware.org` (redirect to www). Vercel shows the exact records.
4. Namecheap → Domain List → lynxware.org → Manage → Advanced DNS:
   - delete the three `A @` records `185.230.63.107`, `185.230.63.171`, `185.230.63.186`; add `A @ 76.76.21.21` (or the value Vercel shows);
   - change `CNAME www` from `cdn1.wixdns.net` to the value Vercel shows (`cname.vercel-dns.com` or a project-specific `*.vercel-dns-0xx.com`).
   - **Leave everything else**: the `v4` CNAME, the MX records (email forwarding) and the SPF TXT.
5. Wait until Vercel shows both domains "Valid Configuration" and has issued certificates; open https://www.lynxware.org and https://lynxware.org, submit one test form.
6. Wix → Settings → Domains: disconnect lynxware.org (stops Wix answering for it).
7. After about a week without issues: cancel the Wix Premium plan (Wix → Subscriptions). The free Wix site can stay as a cold backup.
8. Upgrade the Vercel team to Pro.

## 7. Export from Wix before cancelling

- Forms & Submissions: each form (Contact, Application, Partnership) → Export as CSV. Past submissions are only stored there.
- Contacts (CRM): Contacts → More actions → Export.
- Media Manager: check for files not linked on the site. Everything the site links is already in this repository: 39 originals in `archive/wix-media-originals/`, the 11 downloads in `public/_files/archives/`.
- Billing: download Wix invoices for the books.

## 8. Rollback

Wix is cancelled, so rollback is now only within Vercel (Deployments → an earlier deployment → Promote to Production). Before cancellation it was a DNS edit: restore `A @` 185.230.63.107 / .171 / .186 and `CNAME www` → `cdn1.wixdns.net` in Namecheap and reconnect the domain in Wix. With the TTL at 5 min it takes effect within minutes. After cancelling Wix, roll back within Vercel instead (Deployments → an earlier deployment → Promote to Production).
