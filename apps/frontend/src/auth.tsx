import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "./lib/api";

type AuthContextValue = {
  authenticated: boolean;
  ready: boolean;
  login: (pairingCode: string) => Promise<boolean>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    api.getAuthSession()
      .then((session) => { if (active) setAuthenticated(session.authenticated); })
      .catch(() => { if (active) setAuthenticated(false); })
      .finally(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    authenticated,
    ready,
    login: async (pairingCode) => {
      try {
        const session = await api.login(pairingCode);
        setAuthenticated(session.authenticated);
        return session.authenticated;
      } catch {
        setAuthenticated(false);
        return false;
      }
    },
    logout: async () => {
      // Keep the authenticated UI state if the server cannot revoke the session.
      await api.logout();
      setAuthenticated(false);
    },
  }), [authenticated, ready]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
