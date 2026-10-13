import { generateRegistrationOptions, verifyRegistrationResponse, generateAuthenticationOptions, verifyAuthenticationResponse } from '@simplewebauthn/server';

const SESSION_TTL = 60 * 60 * 1000;
const CHALLENGE_TTL = 5 * 60 * 1000;
const encoder = new TextEncoder();
const cookieNames = { session: 'pds8_session', flow: 'pds8_flow' };
const json = (data, status = 200, headers = {}) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers } });
class HttpError extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
const fail = (status, code, message) => { throw new HttpError(status, code, message); };
function base64url(bytes) { let binary = ''; for (const byte of bytes) binary += String.fromCharCode(byte); return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', ''); }
function bytes(value) { const binary = atob(value.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - value.length % 4) % 4)); return Uint8Array.from(binary, char => char.charCodeAt(0)); }
function random() { return base64url(crypto.getRandomValues(new Uint8Array(32))); }
async function digest(value) { return base64url(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value)))); }
function cookies(request) { const result = {}; for (const part of (request.headers.get('cookie') || '').split(';')) { const at = part.indexOf('='); if (at > 0) result[part.slice(0, at).trim()] = part.slice(at + 1).trim(); } return result; }
function cookie(name, value, seconds, origin) { return `${name}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${seconds}${origin.startsWith('https:') ? '; Secure' : ''}`; }
function withCookies(response, list) { for (const item of list) response.headers.append('Set-Cookie', item); return response; }
function config(env) {
 if (!env.DB || !env.APP_ORIGIN) fail(503, 'not_configured', '인증 서버 설정을 확인해주세요.');
 const origin = new URL(env.APP_ORIGIN);
 if (origin.origin !== env.APP_ORIGIN || (origin.protocol !== 'https:' && !(origin.protocol === 'http:' && origin.hostname === 'localhost'))) fail(503, 'not_configured', '인증 서버의 허용 주소 설정을 확인해주세요.');
 return { origin: origin.origin, rpID: origin.hostname };
}
async function body(request) { if (Number(request.headers.get('content-length') || 0) > 262144) fail(413, 'body_too_large', '요청 크기가 너무 큽니다.'); const text = await request.text(); if (text.length > 262144) fail(413, 'body_too_large', '요청 크기가 너무 큽니다.'); try { const value = JSON.parse(text); if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(); return value; } catch { fail(400, 'invalid_body', '요청 형식을 확인해주세요.'); } }
function username(value) { const name = typeof value === 'string' ? value.trim().toLowerCase() : ''; if (!/^[a-z0-9][a-z0-9_-]{2,31}$/.test(name)) fail(400, 'invalid_username', '아이디는 영문 소문자·숫자·_·-로 3~32자리 입력해주세요. 실제 개인정보 대신 별칭을 사용해주세요.'); return name; }
function credentialName(value) { const name = typeof value === 'string' ? value.trim() : ''; if (!name || name.length > 60 || /[\u0000-\u001f]/.test(name)) fail(400, 'invalid_name', '패스키 이름을 1~60자로 입력해주세요.'); return name; }
async function current(request, env) {
 const token = cookies(request)[cookieNames.session]; if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) return null;
 return env.DB.prepare('SELECT s.account_id AS id, a.username, s.credential_id AS credentialId, s.token_hash AS tokenHash FROM sessions s JOIN accounts a ON a.id=s.account_id JOIN credentials c ON c.id=s.credential_id AND c.account_id=s.account_id WHERE s.token_hash=? AND s.expires_at>?').bind(await digest(token), Date.now()).first();
}
async function requireUser(request, env) { const user = await current(request, env); if (!user) fail(401, 'authentication_required', '패스키로 로그인해주세요. 세션이 만료되었을 수 있습니다.'); return user; }
function publicUser(user) { return { id: user.id, username: user.username }; }
async function storeFlow(env, cfg, data) {
 const flow = random(); const now = Date.now();
 await env.DB.prepare('INSERT INTO challenges (flow_hash,challenge,kind,account_id,username,credential_name,is_new,created_at,expires_at,used) VALUES (?,?,?,?,?,?,?,?,?,0)').bind(await digest(flow), data.challenge, data.kind, data.accountId || null, data.username || null, data.name || null, data.isNew ? 1 : 0, now, now + CHALLENGE_TTL).run();
 return cookie(cookieNames.flow, flow, CHALLENGE_TTL / 1000, cfg.origin);
}
async function consumeFlow(request, env, kind) {
 const flow = cookies(request)[cookieNames.flow]; if (!flow || !/^[A-Za-z0-9_-]{43}$/.test(flow)) fail(400, 'challenge_missing', '인증 요청이 만료되었습니다. 처음부터 다시 시도해주세요.');
 // UPDATE ... RETURNING is a single atomic operation: concurrent verification can consume this challenge only once.
 const row = await env.DB.prepare('UPDATE challenges SET used=1 WHERE flow_hash=? AND kind=? AND used=0 AND expires_at>? RETURNING *').bind(await digest(flow), kind, Date.now()).first();
 if (!row) fail(400, 'challenge_expired_or_used', '이미 사용했거나 만료된 인증 요청입니다. 다시 시작해주세요.');
 return row;
}
async function createSession(env, cfg, user, credentialId) {
 const token = random(); const now = Date.now();
 await env.DB.prepare('INSERT INTO sessions (token_hash,account_id,credential_id,created_at,expires_at) VALUES (?,?,?,?,?)').bind(await digest(token), user.id, credentialId, now, now + SESSION_TTL).run();
 return withCookies(json({ ok: true, user: publicUser(user) }), [cookie(cookieNames.session, token, SESSION_TTL / 1000, cfg.origin), cookie(cookieNames.flow, '', 0, cfg.origin)]);
}
async function limit(request, env, kind) {
 const ip = request.headers.get('CF-Connecting-IP'); if (!ip) return;
 const now = Date.now(); const interval = Math.floor(now / 600000);
 const bucket = await digest(`${env.RATE_LIMIT_SALT || env.APP_ORIGIN}|${ip}|${interval}|${kind}`);
 const row = await env.DB.prepare('INSERT INTO request_limits (bucket,attempt_count,expires_at) VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET attempt_count=attempt_count+1 RETURNING attempt_count').bind(bucket, now + 600000).first();
 if (row.attempt_count > 40) fail(429, 'rate_limited', '인증 요청이 많습니다. 잠시 후 다시 시도해주세요.');
 await env.DB.batch([env.DB.prepare('DELETE FROM request_limits WHERE expires_at<?').bind(now), env.DB.prepare('DELETE FROM challenges WHERE expires_at<?').bind(now - 3600000), env.DB.prepare('DELETE FROM sessions WHERE expires_at<?').bind(now)]);
}
async function registrationOptions(request, env, cfg) {
 const payload = await body(request); const user = payload.mode === 'add' ? await requireUser(request, env) : await current(request, env); const handle = user ? user.username : username(payload.username); const name = credentialName(payload.name);
 if (!user && await env.DB.prepare('SELECT id FROM accounts WHERE username=?').bind(handle).first()) fail(409, 'username_unavailable', '이미 사용 중인 아이디입니다. 기존 계정은 패스키로 로그인한 뒤 추가해주세요.');
 const accountId = user ? user.id : crypto.randomUUID();
 const existing = user ? (await env.DB.prepare('SELECT id,transports FROM credentials WHERE account_id=?').bind(user.id).all()).results : [];
 if (existing.length >= 10) fail(409, 'credential_limit', '패스키는 계정당 최대 10개 등록할 수 있습니다.');
 const options = await generateRegistrationOptions({ rpName: '김희망 · Private Space', rpID: cfg.rpID, userID: encoder.encode(accountId), userName: handle, userDisplayName: handle, attestationType: 'none', excludeCredentials: existing.map(row => ({ id: row.id, transports: JSON.parse(row.transports) })), authenticatorSelection: { residentKey: 'required', userVerification: 'required' }, supportedAlgorithmIDs: [-7, -257], timeout: 60000 });
 const flowCookie = await storeFlow(env, cfg, { kind: 'register', challenge: options.challenge, accountId, username: handle, name, isNew: !user });
 return withCookies(json({ options }), [flowCookie]);
}
async function registrationVerify(request, env, cfg) {
 const payload = await body(request); const flow = await consumeFlow(request, env, 'register');
 if (!flow.is_new) { const user = await requireUser(request, env); if (user.id !== flow.account_id) fail(403, 'account_mismatch', '패스키를 추가할 계정이 달라졌습니다. 다시 시작해주세요.'); }
 let verification; try { verification = await verifyRegistrationResponse({ response: payload, expectedChallenge: flow.challenge, expectedOrigin: cfg.origin, expectedRPID: cfg.rpID, requireUserVerification: true }); } catch { fail(400, 'registration_rejected', '패스키 등록 응답을 확인할 수 없습니다. 다시 등록해주세요.'); }
 if (!verification.verified || !verification.registrationInfo) fail(400, 'registration_rejected', '패스키 등록 검증에 실패했습니다.');
 const info = verification.registrationInfo; const credential = info.credential; const now = Date.now(); const queries = [];
 if (flow.is_new) {
  queries.push(env.DB.prepare('INSERT INTO accounts (id,username,created_at) VALUES (?,?,?)').bind(flow.account_id, flow.username, now));
  // Fictional private examples exist only in the database after a verified registration, never in the anonymous HTML.
  const examples = [['프로젝트 메모', `${flow.username}의 가상 프로젝트: 접근성 좋은 개인 공간을 준비합니다.`], ['지원처 목록', `${flow.username}의 가상 지원처: 별빛 연구소, 푸른 네트워크 팀. 실제 기관 정보가 아닙니다.`], ['나만의 회고', `${flow.username}의 가상 회고: 작은 개선을 기록하며 다음 실험을 준비합니다.`]];
  for (const [title, content] of examples) queries.push(env.DB.prepare('INSERT INTO vault_items (id,account_id,title,content) VALUES (?,?,?,?)').bind(crypto.randomUUID(), flow.account_id, title, content));
 }
 queries.push(env.DB.prepare('INSERT INTO credentials (id,account_id,public_key,counter,name,created_at,transports,device_type,backed_up) VALUES (?,?,?,?,?,?,?,?,?)').bind(credential.id, flow.account_id, base64url(credential.publicKey), credential.counter, flow.credential_name, now, JSON.stringify(credential.transports || []), info.credentialDeviceType, info.credentialBackedUp ? 1 : 0));
 try { await env.DB.batch(queries); } catch { fail(409, 'registration_conflict', '아이디 또는 패스키가 이미 등록되었습니다. 새 요청으로 다시 시도해주세요.'); }
 return createSession(env, cfg, { id: flow.account_id, username: flow.username }, credential.id);
}
async function authenticationOptions(env, cfg) {
 const options = await generateAuthenticationOptions({ rpID: cfg.rpID, userVerification: 'required', timeout: 60000 });
 return withCookies(json({ options }), [await storeFlow(env, cfg, { kind: 'authenticate', challenge: options.challenge })]);
}
async function authenticationVerify(request, env, cfg) {
 const payload = await body(request); const flow = await consumeFlow(request, env, 'authenticate');
 if (typeof payload.id !== 'string' || payload.id.length > 2048) fail(400, 'authentication_rejected', '패스키 응답 형식을 확인해주세요.');
 const credential = await env.DB.prepare('SELECT c.*,a.username FROM credentials c JOIN accounts a ON a.id=c.account_id WHERE c.id=?').bind(payload.id).first();
 if (!credential) fail(401, 'authentication_rejected', '등록된 패스키를 확인할 수 없습니다. 삭제된 패스키는 사용할 수 없습니다.');
 if (payload.response?.userHandle && payload.response.userHandle !== base64url(encoder.encode(credential.account_id))) fail(401, 'authentication_rejected', '패스키의 계정 정보가 일치하지 않습니다.');
 let verification; try { verification = await verifyAuthenticationResponse({ response: payload, expectedChallenge: flow.challenge, expectedOrigin: cfg.origin, expectedRPID: cfg.rpID, requireUserVerification: true, credential: { id: credential.id, publicKey: bytes(credential.public_key), counter: credential.counter, transports: JSON.parse(credential.transports) } }); } catch { fail(401, 'authentication_rejected', '패스키 서명을 확인할 수 없습니다. 다시 로그인해주세요.'); }
 if (!verification.verified) fail(401, 'authentication_rejected', '패스키 서명 검증에 실패했습니다.');
 // Conditional update also denies races with credential deletion or a concurrent counter update.
 const updated = await env.DB.prepare('UPDATE credentials SET counter=?,backed_up=? WHERE id=? AND counter=? RETURNING id').bind(verification.authenticationInfo.newCounter, verification.authenticationInfo.credentialBackedUp ? 1 : 0, credential.id, credential.counter).first();
 if (!updated) fail(401, 'authentication_rejected', '패스키 상태가 변경되었습니다. 다시 로그인해주세요.');
 return createSession(env, cfg, { id: credential.account_id, username: credential.username }, credential.id);
}

export async function handleApi(request, env) {
 const url = new URL(request.url); if (!url.pathname.startsWith('/api/')) return null;
 try {
  const cfg = config(env);
  if (request.method !== 'GET') {
   if (request.headers.get('origin') !== cfg.origin) fail(403, 'origin_denied', '허용되지 않은 주소에서 보낸 요청입니다.');
   if (request.headers.get('content-type')?.split(';')[0].trim() !== 'application/json') fail(415, 'json_required', 'JSON 형식으로 요청해주세요.');
  }
  const path = url.pathname; const method = request.method;
  if (method === 'GET' && path === '/api/session') { const user = await current(request, env); return user ? json({ authenticated: true, user: publicUser(user) }) : json({ authenticated: false }); }
  if (method === 'POST' && ['/api/passkeys/register/options', '/api/passkeys/register/verify', '/api/passkeys/authenticate/options', '/api/passkeys/authenticate/verify'].includes(path)) await limit(request, env, path);
  if (method === 'POST' && path === '/api/passkeys/register/options') return await registrationOptions(request, env, cfg);
  if (method === 'POST' && path === '/api/passkeys/register/verify') return await registrationVerify(request, env, cfg);
  if (method === 'POST' && path === '/api/passkeys/authenticate/options') return await authenticationOptions(env, cfg);
  if (method === 'POST' && path === '/api/passkeys/authenticate/verify') return await authenticationVerify(request, env, cfg);
  if (method === 'POST' && path === '/api/passkeys/register/cancel') { const flow = cookies(request)[cookieNames.flow]; if (flow) await env.DB.prepare('UPDATE challenges SET used=1 WHERE flow_hash=?').bind(await digest(flow)).run(); return withCookies(json({ ok: true }), [cookie(cookieNames.flow, '', 0, cfg.origin)]); }
  if (method === 'POST' && path === '/api/logout') { const token = cookies(request)[cookieNames.session]; if (token) await env.DB.prepare('DELETE FROM sessions WHERE token_hash=?').bind(await digest(token)).run(); return withCookies(json({ ok: true }), [cookie(cookieNames.session, '', 0, cfg.origin), cookie(cookieNames.flow, '', 0, cfg.origin)]); }
  if (method === 'GET' && (path === '/api/vault' || path.startsWith('/api/vault/'))) { const user = await requireUser(request, env); if (path !== '/api/vault' && decodeURIComponent(path.slice('/api/vault/'.length)) !== user.id) fail(403, 'owner_denied', '다른 계정의 비공개 자료는 열 수 없습니다.'); const items = (await env.DB.prepare('SELECT id,title,content FROM vault_items WHERE account_id=? ORDER BY rowid').bind(user.id).all()).results; return json({ user: publicUser(user), items, count: items.length }); }
  if (method === 'GET' && path === '/api/passkeys') { const user = await requireUser(request, env); const rows = (await env.DB.prepare('SELECT id,name,created_at,device_type,backed_up FROM credentials WHERE account_id=? ORDER BY created_at,id').bind(user.id).all()).results; return json({ passkeys: rows.map(row => ({ id: row.id, name: row.name, createdAt: new Date(row.created_at).toISOString(), deviceType: row.device_type, backedUp: !!row.backed_up })), warning: '모든 패스키를 잃거나 삭제하면 이 계정과 비공개 자료에 다시 접근할 수 없습니다. 인증 우회 복구는 제공하지 않습니다. 서로 다른 패스키 두 개를 보관해주세요.' }); }
  if (method === 'GET' && path === '/api/passkeys/evidence') { const user = await requireUser(request, env); const rows = (await env.DB.prepare('SELECT id,name,public_key,counter,created_at,device_type,backed_up FROM credentials WHERE account_id=? ORDER BY created_at,id').bind(user.id).all()).results; return json({ user: publicUser(user), keyFormat: 'COSE public key encoded as base64url; NOT a password or private key', passkeys: rows.map(row => ({ id: row.id, name: row.name, publicKey: row.public_key, counter: row.counter, createdAt: new Date(row.created_at).toISOString(), deviceType: row.device_type, backedUp: !!row.backed_up })) }); }
  if (method === 'DELETE' && path.startsWith('/api/passkeys/')) {
   const user = await requireUser(request, env); const payload = await body(request); if (payload.confirm !== true) fail(400, 'confirmation_required', '삭제할 패스키를 확인해주세요.');
   const id = decodeURIComponent(path.slice('/api/passkeys/'.length)); const row = await env.DB.prepare('SELECT id FROM credentials WHERE id=? AND account_id=?').bind(id, user.id).first(); if (!row) fail(403, 'owner_denied', '본인이 등록한 패스키만 삭제할 수 있습니다.');
   await env.DB.batch([env.DB.prepare('DELETE FROM credentials WHERE id=? AND account_id=?').bind(id, user.id), env.DB.prepare('DELETE FROM sessions WHERE credential_id=? AND account_id=?').bind(id, user.id)]);
   const remaining = (await env.DB.prepare('SELECT COUNT(*) AS count FROM credentials WHERE account_id=?').bind(user.id).first()).count;
   const loggedOut = user.credentialId === id || remaining === 0; const response = json({ ok: true, remaining, loggedOut });
   return loggedOut ? withCookies(response, [cookie(cookieNames.session, '', 0, cfg.origin)]) : response;
  }
  fail(404, 'not_found', '요청한 기능을 찾을 수 없습니다.');
 } catch (error) {
  if (error instanceof HttpError) return json({ error: error.code, message: error.message }, error.status);
  // Never expose DB errors, WebAuthn bodies, cookies, tokens, or private information in errors/logs.
  return json({ error: 'server_error', message: '요청 처리 중 문제가 생겼습니다. 잠시 후 다시 시도해주세요.' }, 500);
 }
}
