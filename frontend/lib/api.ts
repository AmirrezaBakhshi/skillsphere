import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL,
  withCredentials: true, // sends the httponly refresh cookie on same-site requests
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshInFlight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const response = await axios.post(
    `${baseURL}/auth/refresh/`,
    {},
    { withCredentials: true }
  );
  const newAccessToken = response.data.access as string;
  useAuthStore.getState().setAccessToken(newAccessToken);
  return newAccessToken;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = ["/auth/login/", "/auth/register/", "/auth/refresh/"].some((p) =>
      originalRequest.url?.includes(p)
    );

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      try {
        refreshInFlight = refreshInFlight ?? refreshAccessToken();
        const newAccessToken = await refreshInFlight;
        refreshInFlight = null;
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        refreshInFlight = null;
        useAuthStore.getState().clearSession();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
