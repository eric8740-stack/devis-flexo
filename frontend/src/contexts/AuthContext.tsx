"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import type { LoginRequest, RegisterRequest, User } from "@/types/auth";

// Consolidation audit 05/07/2026 : API_URL, tokens et refresh (dédupliqué)
// viennent du module unique auth-tokens.ts — plus de logique dupliquée ici.
import {
  API_URL,
  clearTokens,
  getAccessToken,
  refreshAccessToken,
  setTokens,
} from "@/lib/auth-tokens";

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const initAuth = async () => {
      const token = getAccessToken();
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
          const newToken = await refreshAccessToken();
          if (newToken) {
            const refreshed = await fetchMe(newToken);
            if (refreshed) setUser(refreshed);
          } else {
            // Refresh KO → clear tokens (mais on ne redirige pas ici,
            // ProtectedRoute s'en charge si la route le demande)
            clearTokens();
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
    setTokens(tokens.access_token, tokens.refresh_token);

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
    clearTokens();
    setUser(null);
    router.push("/login");
  };

  const refreshUser = async () => {
    const token = getAccessToken();
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
