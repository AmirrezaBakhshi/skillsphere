import { api } from "@/lib/api";
import { AuthUser } from "@/store/authStore";

type AuthResponse = {
  user: AuthUser;
  access: string;
};

export async function registerAccount(payload: {
  email: string;
  username: string;
  password: string;
}): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/register/", payload);
  return data;
}

export async function login(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/login/", payload);
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout/");
}
