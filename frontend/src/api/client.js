import axios from "axios";

// Empty by default: the API is served from the same origin (Vite proxy in dev, nginx in production).
const API_URL = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: `${API_URL}/api`,
});

api.interceptors.request.use((config) => {
  const access = localStorage.getItem("access_token");
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return Promise.reject(error);

    original._retry = true;
    try {
      if (!refreshing) {
        refreshing = axios
          .post(`${API_URL}/api/auth/refresh`, { refresh_token: refresh })
          .then((r) => {
            localStorage.setItem("access_token", r.data.access_token);
            localStorage.setItem("refresh_token", r.data.refresh_token);
            return r.data.access_token;
          })
          .finally(() => {
            refreshing = null;
          });
      }
      const token = await refreshing;
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    } catch (e) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      return Promise.reject(e);
    }
  }
);

export default api;
