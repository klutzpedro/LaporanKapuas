import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("bais_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Terjadi kesalahan. Silakan coba lagi.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const ROLE_LABEL = {
  admin: "ADMIN",
  piket: "PIKET",
  tim_lid: "TIM LID",
  tim_kontra: "TIM KONTRA",
  tim_gal: "TIM GAL",
  tim_medmon: "TIM MEDMON",
  tim_geoint: "TIM GEOINT",
};

export const COG_LABEL = {
  aceh: "ACEH",
  jakarta: "JAKARTA",
  indonesia: "INDONESIA",
  papua: "PAPUA",
  internasional: "INTERNASIONAL",
};

export const COG_COLOR = {
  aceh: "#10B981",
  jakarta: "#3B82F6",
  indonesia: "#DC2626",
  papua: "#F59E0B",
  internasional: "#8B5CF6",
};
