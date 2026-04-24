import axios from "axios";

const BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

const client = axios.create({ baseURL: BASE });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && !err.config?.url?.includes("/auth/login")) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

const unwrap = (p) => p.then((r) => r.data);

export const api = {
  register: (data) => unwrap(client.post("/auth/register", data)),
  login: (data) => unwrap(client.post("/auth/login", data)),
  logout: () => unwrap(client.post("/auth/logout")),
  me: () => unwrap(client.get("/auth/me")),

  getDashboard: (month) => unwrap(client.get(`/dashboard`, { params: { month } })),

  getTransactions: (params) => unwrap(client.get(`/transactions`, { params })),
  addTransaction: (data) => unwrap(client.post(`/transactions`, data)),
  deleteTransaction: (id) => unwrap(client.delete(`/transactions/${id}`)),

  getBudgets: (month) => unwrap(client.get(`/budgets`, { params: { month } })),
  saveBudgets: (data) => unwrap(client.post(`/budgets`, data)),
  deleteBudget: (id) => unwrap(client.delete(`/budgets/${id}`)),

  getMonthlyCapital: (month) => unwrap(client.get(`/monthly-capital`, { params: { month } })),
  saveMonthlyCapital: (data) => unwrap(client.post(`/monthly-capital`, data)),
  deleteMonthlyCapital: (month) => unwrap(client.delete(`/monthly-capital`, { params: { month } })),

  predict: (n_days) => unwrap(client.post(`/predict`, { n_days })),
  mlHealth: () => unwrap(client.get(`/ml/health`)),

  getPredictionHistory: (page = 1, limit = 10) =>
    unwrap(client.get(`/prediction-history`, { params: { page, limit } })),
  getPredictionDetail: (id) => unwrap(client.get(`/prediction-history/${id}`)),
  deletePrediction: (id) => unwrap(client.delete(`/prediction-history/${id}`)),
};

export default api;
