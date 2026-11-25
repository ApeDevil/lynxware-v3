// POST /api/form: receives the site's contact, application and partnership forms and emails them
// through Resend. No data is stored. Configuration (Vercel project environment variables):
//   RESEND_API_KEY   Resend API key (sensitive)
//   FORM_FROM        verified sender, e.g. "LYNXware Website <forms@lynxware.org>"
//   FORM_TO          recipient(s), comma-separated
//   ALLOWED_ORIGINS  optional, comma-separated extra origins allowed to post (the site's own host is always allowed)

const FORMS = new Set(['Contact', 'Application', 'Partnership Request']);
const MAX_FIELDS = 12;
const MAX_LABEL = 100;
const MAX_VALUE = 5000;
const MIN_ELAPSED_MS = 2500; // humans take longer than this to fill a form
const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}\.[a-zA-Z]{2,63}$/;

// Best-effort per-instance rate limit; the honeypot and timing check do most of the work.
const hits = new Map();
function limited(ip) {
	const now = Date.now();
	const recent = (hits.get(ip) || []).filter((t) => now - t < 10 * 60_000);
	recent.push(now);
	hits.set(ip, recent);
	if (hits.size > 5000) hits.clear();
	return recent.length > 5;
}

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const clean = (s, max) => String(s ?? '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').trim().slice(0, max);

function reply(res, status, body) {
	res.statusCode = status;
	res.setHeader('content-type', 'application/json');
	res.setHeader('cache-control', 'no-store');
	res.end(JSON.stringify(body));
}

export default async function handler(req, res) {
	if (req.method !== 'POST') return reply(res, 405, { error: 'Method not allowed' });

	const host = req.headers['x-forwarded-host'] || req.headers.host;
	const origin = req.headers.origin;
	const allowed = [`https://${host}`, ...(process.env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean)];
	if (!origin || !allowed.includes(origin)) return reply(res, 403, { error: 'Forbidden' });

	const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
	if (limited(ip)) return reply(res, 429, { error: 'Too many requests, please try again later' });

	let body = req.body;
	if (typeof body === 'string') {
		try {
			body = JSON.parse(body);
		} catch {
			return reply(res, 400, { error: 'Invalid request' });
		}
	}
	if (!body || typeof body !== 'object') return reply(res, 400, { error: 'Invalid request' });

	// Spam traps: a filled honeypot or an instant submit gets a fake success, so bots learn nothing.
	if (body.company_website || !(Number(body.elapsed) >= MIN_ELAPSED_MS)) return reply(res, 200, { ok: true });

	const form = clean(body.form, 60);
	if (!FORMS.has(form)) return reply(res, 400, { error: 'Unknown form' });
	if (!Array.isArray(body.fields) || body.fields.length === 0 || body.fields.length > MAX_FIELDS) {
		return reply(res, 400, { error: 'Invalid fields' });
	}
	const fields = body.fields.map((f) => ({
		label: clean(f?.label, MAX_LABEL),
		type: clean(f?.type, 20),
		value: clean(f?.value, MAX_VALUE),
	}));
	const email = fields.find((f) => f.type === 'email')?.value || '';
	if (!EMAIL.test(email)) return reply(res, 400, { error: 'Please enter a valid email address' });
	for (const f of fields) {
		if (f.type === 'url' && f.value && !/^((https?|ftp):\/\/)?[^\s/$.?#]*\.[^\s]*$/.test(f.value)) {
			return reply(res, 400, { error: `Invalid link in "${f.label}"` });
		}
	}

	const { RESEND_API_KEY, FORM_FROM, FORM_TO } = process.env;
	if (!RESEND_API_KEY || !FORM_FROM || !FORM_TO) return reply(res, 503, { error: 'Form delivery is not configured yet' });

	const page = clean(body.page, 100);
	const text = `${form} form on www.lynxware.org${page}\n\n${fields.map((f) => `${f.label}:\n${f.value || '-'}`).join('\n\n')}\n`;
	const html = `<h2>${esc(form)}</h2><p>Sent from www.lynxware.org${esc(page)}</p><table cellpadding="6">${fields
		.map((f) => `<tr><th align="left" valign="top">${esc(f.label)}</th><td style="white-space:pre-wrap">${esc(f.value || '-')}</td></tr>`)
		.join('')}</table>`;

	const r = await fetch('https://api.resend.com/emails', {
		method: 'POST',
		headers: { authorization: `Bearer ${RESEND_API_KEY}`, 'content-type': 'application/json' },
		body: JSON.stringify({
			from: FORM_FROM,
			to: FORM_TO.split(',').map((s) => s.trim()),
			reply_to: email,
			subject: `[lynxware.org] ${form}: ${email}`,
			text,
			html,
		}),
	});
	if (!r.ok) {
		console.error('resend failed', r.status, await r.text().catch(() => ''));
		return reply(res, 502, { error: 'The message could not be delivered' });
	}
	return reply(res, 200, { ok: true });
}
