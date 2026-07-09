import { create } from "zustand";

export type AuthUser = {
  id: string;
  email: string;
  username: string;
  is_staff: boolean;
  date_joined: string;
};

type AuthState = {
  accessToken: string | null;
  user: AuthUser | null;
  setSession: (accessToken: string, user: AuthUser) => void;
  setAccessToken: (accessToken: string) => void;
  clearSession: () => void;
};

/**
 * Deliberately in-memory only. The access token never touches
 * localStorage/sessionStorage/cookies from the frontend side - if this
 * tab reloads, the refresh cookie (httponly, backend-only) is used via
 * /auth/refresh/ to get a new one. See lib/api.ts.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ accessToken, user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  clearSession: () => set({ accessToken: null, user: null }),
}));
