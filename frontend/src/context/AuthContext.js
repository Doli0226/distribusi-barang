import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api.get("/auth/me").then((r) => setUser(r.data.user)).catch(() => setUser(null)).finally(() => setReady(true));
  }, []);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    setUser(r.data.user);
    return r.data.user;
  };
  const register = async (payload) => {
    const r = await api.post("/auth/register", payload);
    setUser(r.data.user);
    return r.data.user;
  };
  const logout = async () => { try { await api.post("/auth/logout"); } finally { setUser(null); } };
  const refresh = async () => { const r = await api.get("/auth/me"); setUser(r.data.user); };

  return (
    <AuthCtx.Provider value={{ user, ready, login, logout, register, refresh, isAdmin: user?.role === "admin" }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
