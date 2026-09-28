import { ENDPOINTS } from "../config/api";

const SESSION_KEY = "rescuesync.session";
const SESSION_EVENT = "rescuesync-session";

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function getSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    return session?.access_token && session.expiresAt > Date.now() ? session : null;
  } catch {
    return null;
  }
}

export function subscribeSession(listener) {
  window.addEventListener(SESSION_EVENT, listener);
  return () => window.removeEventListener(SESSION_EVENT, listener);
}

export async function login(username, password) {
  let response;
  try {
    response = await fetch(ENDPOINTS.LOGIN, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  } catch {
    throw new Error("No se pudo conectar con el servidor. Intentá nuevamente.");
  }
  if (!response.ok) {
    throw new Error(response.status === 401
      ? "No se pudo iniciar sesión. Verificá tu usuario y contraseña."
      : "El servidor no pudo iniciar sesión. Intentá nuevamente.");
  }
  const data = await response.json();
  if (typeof data.access_token !== "string" || !data.access_token ||
      data.token_type?.toLowerCase() !== "bearer" ||
      !Number.isFinite(data.expires_in) || data.expires_in <= 0) {
    throw new Error("El servidor devolvió una sesión inválida.");
  }
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({
    access_token: data.access_token,
    expiresAt: Date.now() + data.expires_in * 1000,
    username,
  }));
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export async function authenticatedFetch(url, options = {}) {
  const session = getSession();
  if (!session) {
    clearSession();
    throw new Error("Tu sesión venció. Iniciá sesión nuevamente.");
  }
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) clearSession();
  return response;
}

export async function logout() {
  if (!getSession()) {
    clearSession();
    return;
  }
  let response;
  try {
    response = await authenticatedFetch(ENDPOINTS.LOGOUT, { method: "POST" });
  } catch {
    throw new Error("No se pudo conectar para cerrar sesión. Intentá nuevamente.");
  }
  if (!response.ok && response.status !== 401) {
    throw new Error("No se pudo cerrar sesión en el servidor. Intentá nuevamente.");
  }
  clearSession();
}
