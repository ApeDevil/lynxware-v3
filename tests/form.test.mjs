// node --test tests/  — the /api/form handler with Resend mocked.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import handler from '../api/form.js';

const env = { RESEND_API_KEY: 're_test', FORM_FROM: 'LYNXware <forms@example.org>', FORM_TO: 'owner@example.org' };
const good = () => ({ form: 'Contact', page: '/contact', elapsed: 10000, company_website: '', fields: [
	{ label: 'First name', type: 'text', value: 'Ada' }, { label: 'Email', type: 'email', value: 'ada@example.com' },
	{ label: 'Write a message', type: 'textarea', value: 'Hello <b>there</b>' }] });
let ipn = 0;
async function call(body, { method = 'POST', origin = 'https://www.lynxware.org', vars = env } = {}) {
	Object.assign(process.env, { RESEND_API_KEY: '', FORM_FROM: '', FORM_TO: '' }, vars);
	const sent = [];
	globalThis.fetch = async (url, init) => { sent.push({ url, body: JSON.parse(init.body), auth: init.headers.authorization }); return new Response('{}', { status: 200 }); };
	const req = { method, body, headers: { host: 'www.lynxware.org', origin, 'x-forwarded-for': `10.0.0.${++ipn}` } };
	const res = { statusCode: 0, headers: {}, setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = JSON.parse(b); } };
	await handler(req, res);
	return { status: res.statusCode, body: res.body, sent };
}

test('valid submission is emailed with reply-to and escaped HTML', async () => {
	const r = await call(good());
	assert.equal(r.status, 200);
	assert.equal(r.sent.length, 1);
	assert.equal(r.sent[0].url, 'https://api.resend.com/emails');
	assert.equal(r.sent[0].auth, 'Bearer re_test');
	assert.equal(r.sent[0].body.reply_to, 'ada@example.com');
	assert.deepEqual(r.sent[0].body.to, ['owner@example.org']);
	assert.match(r.sent[0].body.html, /&lt;b&gt;there&lt;\/b&gt;/);
	assert.doesNotMatch(r.sent[0].body.html, /<b>there/);
});
test('honeypot and too-fast submits get a silent fake success, nothing sent', async () => {
	for (const b of [{ ...good(), company_website: 'spam.example' }, { ...good(), elapsed: 300 }]) {
		const r = await call(b); assert.equal(r.status, 200); assert.equal(r.sent.length, 0);
	}
});
test('invalid email, unknown form, bad url, too many fields are rejected', async () => {
	const bad = good(); bad.fields[1].value = 'not-an-email'; assert.equal((await call(bad)).status, 400);
	assert.equal((await call({ ...good(), form: 'Other' })).status, 400);
	const url = good(); url.fields.push({ label: 'Link', type: 'url', value: 'javascript alert' }); assert.equal((await call(url)).status, 400);
	assert.equal((await call({ ...good(), fields: Array(13).fill({ label: 'x', type: 'text', value: 'y' }) })).status, 400);
});
test('foreign origin and non-POST are refused', async () => {
	assert.equal((await call(good(), { origin: 'https://evil.example' })).status, 403);
	assert.equal((await call(good(), { method: 'GET' })).status, 405);
});
test('missing configuration answers 503 without calling Resend', async () => {
	const r = await call(good(), { vars: {} }); assert.equal(r.status, 503); assert.equal(r.sent.length, 0);
});
test('rate limit kicks in after 5 submissions from one address', async () => {
	Object.assign(process.env, env);
	globalThis.fetch = async () => new Response('{}', { status: 200 });
	let last;
	for (let i = 0; i < 6; i++) {
		const req = { method: 'POST', body: good(), headers: { host: 'www.lynxware.org', origin: 'https://www.lynxware.org', 'x-forwarded-for': '192.0.2.1' } };
		const res = { setHeader() {}, end(b) { this.body = b; } }; await handler(req, res); last = res.statusCode;
	}
	assert.equal(last, 429);
});
