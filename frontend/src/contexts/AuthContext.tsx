"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import type { LoginRequest, RegisterRequest, User } from "@/types/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_TOKEN_KEY = "devis_flexo_access_token";
const REFRESH_TOKEN_KEY = "devis_flexo_refresh_token";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function fetchMe(token: string): Promise<User | null> {
  const r = await fetch(`${API_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) return null;
  return (await r.json()) as User;
}

async function tryRefreshTokens(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;
  const r = await fetch(`${API_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!r.ok) return null;
  const tokens = await r.json();
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  return tokens.access_token as string;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await fetchMe(token);
        if (me) {
          setUser(me);
        } else {
          // 401 ou autre : tenter le refresh
          const newToken = await tryRefreshTokens();
          if (newToken) {
            const refreshed = await fetchMe(newToken);
            if (refreshed) setUser(refreshed);
          } else {
            // Refresh KO → clear tokens (mais on ne redirige pas ici,
            // ProtectedRoute s'en charge si la route le demande)
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
          }
        }
      } catch (e) {
        console.error("AuthContext init error:", e);
      } finally {
        setIsLoading(false);
      }
    };
    void initAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (data: LoginRequest) => {
    const r = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Login failed");
    }
    const tokens = await r.json();
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);

    const me = await fetchMe(tokens.access_token);
    if (!me) throw new Error("Impossible de récupérer le profil après login");
    setUser(me);
    router.push("/devis");
  };

  const register = async (data: RegisterRequest) => {
    const r = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Inscription échouée");
    }
    // Pas de login auto : confirmation email d'abord
    router.push("/login?registered=true");
  };

  const logout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setUser(null);
    router.push("/login");
  };

  const refreshUser = async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) return;
    const me = await fetchMe(token);
    if (me) setUser(me);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
