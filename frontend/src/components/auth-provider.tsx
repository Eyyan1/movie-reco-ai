"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  signUp as signUpRequest
} from "@/lib/api";
import type { AuthPayload, AuthUser } from "@/lib/types";

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  login: (payload: AuthPayload) => Promise<void>;
  signUp: (payload: AuthPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser().catch(() => {
      setUser(null);
      setIsLoading(false);
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      async login(payload) {
        const response = await loginRequest(payload);
        setUser(response.user);
      },
      async signUp(payload) {
        const response = await signUpRequest(payload);
        setUser(response.user);
      },
      async logout() {
        await logoutRequest();
        setUser(null);
      },
      refreshUser
    }),
    [user, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
