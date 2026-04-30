/**
 * Auth store — persists the JWT token in localStorage so the user
 * stays logged in across page refreshes. Uses Zustand for simplicity.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  email: string | null;
  setAuth: (token: string, email: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      setAuth: (token, email) => set({ token, email }),
      clearAuth: () => set({ token: null, email: null }),
    }),
    { name: "travel-auth" } // localStorage key
  )
);
