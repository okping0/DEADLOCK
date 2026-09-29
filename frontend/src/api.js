import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function login(username, password) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const res = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
}

export async function register(username, email, password) {
  const res = await api.post("/auth/register", { username, email, password });
  return res.data;
}

export const getStockoutRisk = (warehouseId) =>
  api.get("/intelligence/stockout-risk", { params: { warehouse_id: warehouseId } }).then((r) => r.data);

export const getDeadStockReport = (warehouseId) =>
  api.get("/intelligence/dead-stock", { params: { warehouse_id: warehouseId } }).then((r) => r.data);

export const getForecast = (productId, warehouseId, horizonDays = 30) =>
  api
    .get(`/intelligence/forecast/${productId}`, {
      params: { warehouse_id: warehouseId, horizon_days: horizonDays },
    })
    .then((r) => r.data);

export const getProducts = () => api.get("/products/").then((r) => r.data);
export const getWarehouses = () => api.get("/warehouses/").then((r) => r.data);
export const getStock = (warehouseId) =>
  api.get("/stock/", { params: { warehouse_id: warehouseId } }).then((r) => r.data);

export default api;
