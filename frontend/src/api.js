import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${BASE}/api`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// centralised errors
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg = err?.response?.data?.detail || err.message || "Terjadi kesalahan";
    return Promise.reject({ ...err, message: msg });
  }
);

export const download = async (path, filename) => {
  const res = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
};
