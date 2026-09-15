import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL;

if (!API_BASE_URL) {
  throw new Error(
    "VITE_API_URL is missing! Please set it in your .env file to enable the SEO audit engine.",
  );
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds to allow for deep scans
});

// Add a request interceptor to include the JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    // Axios `auth` sets Basic and replaces Bearer — that is intentional for
    // env superadmin. Otherwise attach the operator JWT.
    if (token && !config.auth) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Add a response interceptor to handle unauthorized errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = String(error.config?.url || "");
    // Do not wipe the operator JWT on Access/admin 401s (stale Basic creds).
    if (
      status === 401 &&
      (url.includes("/token") || url.endsWith("/me") || url.includes("/me?"))
    ) {
      localStorage.removeItem("token");
    }
    return Promise.reject(error);
  },
);

export default api;

export const setAuthToken = (token: string) => {
  localStorage.setItem("token", token);
};

export const logout = () => {
  localStorage.removeItem("token");
};

export const isAuthenticated = () => {
  return !!localStorage.getItem("token");
};
