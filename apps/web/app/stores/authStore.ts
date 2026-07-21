import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  user: Record<string, unknown> | null;
  setToken: (t: string) => void;
  setUser: (u: Record<string, unknown>) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setToken: (t: string) => set({ token: t }),
      setUser: (u: Record<string, unknown>) => set({ user: u }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "memori-auth" }
  )
);

export const getHeaders = (): Record<string, string> => {
  const { token } = useAuthStore.getState();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export const apiUrl = (path: string): string => {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${base}${path}`;
};