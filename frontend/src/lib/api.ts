import axios from "axios";

// NEXT_PUBLIC_ prefix required — this value gets inlined into the client
// bundle at build time by Next.js, since the browser calls the API
// directly (not through a Next.js server proxy). Falls back to localhost
// for local dev without needing a .env.local file present.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// A 401 here means the token is missing/expired — bounce to login rather
// than letting every calling component handle this individually.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      window.localStorage.removeItem("access_token");
      window.localStorage.removeItem("user");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
