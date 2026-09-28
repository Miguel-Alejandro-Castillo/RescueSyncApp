import { createContext, useContext, useEffect, useState } from "react";
import { clearSession, getSession, subscribeSession } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(getSession);
  useEffect(() => subscribeSession(() => setSession(getSession())), []);
  useEffect(() => {
    if (!session) return;
    const checkExpiry = () => {
      if (!getSession()) clearSession();
    };
    const timer = window.setTimeout(checkExpiry, Math.min(session.expiresAt - Date.now(), 2147483647));
    window.addEventListener("focus", checkExpiry);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("focus", checkExpiry);
    };
  }, [session]);
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>;
}

export function useSession() {
  return useContext(AuthContext);
}
