import { neon } from "@neondatabase/serverless";
import { TOKEN_GUIDE_HTML } from "./token_guide_html.js";
import { UPDATES_MANIFEST } from "./updates_manifest.js";

const HTML_OK = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Vexx Cloner</title>
<style>body{background:#08080e;color:#eaeaf4;font-family:Segoe UI,sans-serif;text-align:center;padding:48px}
h1{color:#bf5fff}p{color:#00d9ff}</style></head>
<body><h1>Аккаунт привязан</h1><p>Закрой вкладку и вернись в Discord — клон продолжится в ЛС.</p></body></html>`;

const HTML_FAIL = `<!DOCTYPE html><html><body style="background:#111;color:#f88;text-align:center;padding:48px">
<h1>Ошибка авторизации</h1><p>Вернись в Discord и нажми Authorize снова.</p></body></html>`;

function b64urlDecode(s) {
  let t = String(s).replace(/-/g, "+").replace(/_/g, "/");
  while (t.length % 4) t += "=";
  const bin = atob(t);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmacFirst16(secret, text) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(text)));
  return sig.slice(0, 16);
}

function sigEqual(a, b) {
  if (a.length !== b.length) return false;
  let v = 0;
  for (let i = 0; i < a.length; i++) v |= a[i] ^ b[i];
  return v === 0;
}

async function parseSignedState(state, secret) {
  if (!secret || !state) return null;
  try {
    const bin = b64urlDecode(state);
    if (bin.length < 17) return null;
    const rawBytes = bin.slice(0, bin.length - 16);
    const sig = bin.slice(bin.length - 16);
    const jsonStr = new TextDecoder().decode(rawBytes);
    const expected = await hmacFirst16(secret, jsonStr);
    if (!sigEqual(sig, expected)) return null;
    const payload = JSON.parse(jsonStr);
    if (!payload.u || !payload.e) return null;
    if (Number(payload.e) < Math.floor(Date.now() / 1000)) return null;
    return {
      discord_user_id: String(payload.u),
      source_id: payload.s ? String(payload.s) : "",
      target_id: payload.t ? String(payload.t) : "",
      strategy: payload.st ? String(payload.st) : "2",
    };
  } catch {
    return null;
  }
}

async function exchangeCode(env, code) {
  const body = new URLSearchParams({
    client_id: env.DISCORD_CLIENT_ID,
    client_secret: env.DISCORD_CLIENT_SECRET,
    grant_type: "authorization_code",
    code,
    redirect_uri: env.REDIRECT_URI,
  });
  const r = await fetch("https://discord.com/api/v10/oauth2/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "VexxClonerOAuth/1.0",
    },
    body,
  });
  const data = await r.json();
  if (!r.ok) {
    throw new Error(data.error_description || data.error || "token exchange failed");
  }
  return data;
}

async function fetchMe(accessToken) {
  const r = await fetch("https://discord.com/api/v10/users/@me", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "User-Agent": "VexxClonerOAuth/1.0",
    },
  });
  if (!r.ok) return null;
  return r.json();
}

function oauthToken(access) {
  return `oauth:${access}`;
}

async function loadFlow(sql, state, secret) {
  let flow = await parseSignedState(state, secret);
  if (flow) return flow;
  const rows = await sql`
    DELETE FROM oauth_flows
    WHERE state = ${state} AND expires_at >= NOW()
    RETURNING discord_user_id, source_id, target_id, strategy
  `;
  return rows[0] || null;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/help/token" || url.pathname === "/help/token/") {
      return new Response(TOKEN_GUIDE_HTML, {
        status: 200,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }
    if (url.pathname === "/updates/manifest.json") {
      return new Response(JSON.stringify(UPDATES_MANIFEST), {
        status: 200,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "public, max-age=120",
        },
      });
    }
    if (url.pathname === "/" || url.pathname === "") {
      return new Response("Vexx Cloner OAuth (free workers.dev)", { status: 200 });
    }
    if (!url.pathname.endsWith("/oauth/callback")) {
      return new Response("Not found", { status: 404 });
    }

    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const err = url.searchParams.get("error");
    if (err || !code || !state) {
      return new Response(HTML_FAIL, {
        status: 400,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    const sql = neon(env.DATABASE_URL);

    try {
      const flow = await loadFlow(sql, state, env.DISCORD_CLIENT_SECRET);
      if (!flow) {
        console.error("oauth: invalid or expired state");
        return new Response(HTML_FAIL, {
          status: 400,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }

      const tokenResp = await exchangeCode(env, code);
      const access = tokenResp.access_token;
      if (!access) throw new Error("no access_token");

      const me = await fetchMe(access);
      if (!me || String(me.id) !== String(flow.discord_user_id)) {
        throw new Error("user id mismatch");
      }

      const refresh = tokenResp.refresh_token || null;
      const expiresIn = Number(tokenResp.expires_in || 3600);
      const exp = new Date(Date.now() + Math.max(expiresIn - 30, 60) * 1000).toISOString();
      const token = oauthToken(access);
      const username = me.username || "";
      const globalName = me.global_name || "";

      await sql`
        INSERT INTO cloner_accounts
          (discord_user_id, username, global_name, token, lang,
           refresh_token, token_expires_at, last_used_at, updated_at)
        VALUES
          (${String(flow.discord_user_id)}, ${username}, ${globalName}, ${token}, 'ru',
           ${refresh}, ${exp}::timestamptz, NOW(), NOW())
        ON CONFLICT (discord_user_id) DO UPDATE SET
          username = EXCLUDED.username,
          global_name = EXCLUDED.global_name,
          token = EXCLUDED.token,
          refresh_token = COALESCE(EXCLUDED.refresh_token, cloner_accounts.refresh_token),
          token_expires_at = EXCLUDED.token_expires_at,
          last_used_at = NOW(),
          updated_at = NOW()
      `;

      if (flow.source_id && flow.target_id) {
        await sql`
          INSERT INTO bot_clone_queue
            (discord_user_id, source_id, target_id, strategy, status)
          VALUES
            (${String(flow.discord_user_id)}, ${String(flow.source_id)},
             ${String(flow.target_id)}, ${String(flow.strategy || "2")}, 'pending')
        `;
      }

      return new Response(HTML_OK, {
        status: 200,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    } catch (e) {
      console.error("oauth callback:", e);
      return new Response(HTML_FAIL, {
        status: 500,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }
  },
};
