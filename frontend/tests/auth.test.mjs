import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

// Replace only Vite's environment-dependent config; exercise the actual service.
const source = (await readFile(new URL("../src/services/authService.js", import.meta.url), "utf8"))
  .replace('import { ENDPOINTS } from "../config/api";',
    'const ENDPOINTS = { LOGIN: "/api/rescue/auth/login", LOGOUT: "/api/rescue/auth/logout" };');
const auth = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
beforeEach(() => {
  const storage = new Map();
  globalThis.sessionStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
  };
  globalThis.window = new EventTarget();
});
const success = () => Response.json({ access_token: "test-token", token_type: "bearer", expires_in: 3600 });

test("login sends the Bonita username/password contract and retains session", async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/api/rescue/auth/login");
    assert.equal(options.method, "POST");
    assert.deepEqual(JSON.parse(options.body), { username: "walter.bates", password: " secret " });
    return success();
  };
  await auth.login("walter.bates", " secret ");
  assert.equal(auth.getSession().access_token, "test-token");
  assert.equal(sessionStorage.getItem("rescuesync.session").includes("secret"), false);
});

test("invalid credentials never create a session", async () => {
  globalThis.fetch = async () => new Response(null, { status: 401 });
  await assert.rejects(auth.login("user", "wrong"), /usuario y contraseña/);
  assert.equal(auth.getSession(), null);
});

test("logout sends Bearer token, accepts empty 204 and clears session", async () => {
  globalThis.fetch = async () => success();
  await auth.login("user", "password");
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/api/rescue/auth/logout");
    assert.equal(options.method, "POST");
    assert.equal(options.headers.get("Authorization"), "Bearer test-token");
    return new Response(null, { status: 204 });
  };
  await auth.logout();
  assert.equal(auth.getSession(), null);
});

test("network failure on logout retains session for retry", async () => {
  globalThis.fetch = async () => success();
  await auth.login("user", "password");
  globalThis.fetch = async () => { throw new TypeError("offline"); };
  await assert.rejects(auth.logout(), /Intentá nuevamente/);
  assert.ok(auth.getSession());
});

test("expired sessions and API 401 require login again", async () => {
  sessionStorage.setItem("rescuesync.session", JSON.stringify({ access_token: "expired", expiresAt: Date.now() - 1 }));
  await assert.rejects(auth.authenticatedFetch("/resource"), /venció/);
  globalThis.fetch = async () => success();
  await auth.login("user", "password");
  globalThis.fetch = async () => new Response(null, { status: 401 });
  await auth.authenticatedFetch("/resource");
  assert.equal(auth.getSession(), null);
});

test("malformed successful response cannot create a session", async () => {
  globalThis.fetch = async () => Response.json({ access_token: "token" });
  await assert.rejects(auth.login("user", "password"), /inválida/);
  assert.equal(auth.getSession(), null);
});
