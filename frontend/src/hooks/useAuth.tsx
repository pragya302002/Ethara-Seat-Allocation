"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { LoginResponse, UserRole } from "@/types";

interface AuthUser {
  employee_id: string;
  full_name: string;
  role: UserRole;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const stored = window.localStorage.getItem("user");
    if (stored) {
      setUser(JSON.parse(stored));
    }
    setIsLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const { data } = await api.post<LoginResponse>("/auth/login", { email, password });
    const authUser: AuthUser = { employee_id: data.employee_id, full_name: data.full_name, role: data.role };
    window.localStorage.setItem("access_token", data.access_token);
    window.localStorage.setItem("user", JSON.stringify(authUser));
    setUser(authUser);
    router.push("/dashboard");
  }

  function logout() {
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("user");
    setUser(null);
    router.push("/login");
  }

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
