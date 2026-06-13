/**
 * Cliente HTTP para la API de PropTech PDE.
 * Usa axios con interceptors para JWT y manejo de errores.
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

// Por defecto se usan rutas RELATIVAS (/api/v1) que Next.js proxea al backend.
// Así el navegador solo habla con el dominio del frontend (un único túnel,
// sin CORS ni acople de URLs). Se puede forzar una URL absoluta con la env var.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ─── REQUEST INTERCEPTOR ───────────────────────────────────────
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Agregar JWT token si existe
    const token = typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// ─── RESPONSE INTERCEPTOR ─────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Auto-refresh en 401
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) {
          throw new Error("No refresh token");
        }

        const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;
        localStorage.setItem("access_token", access_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch {
        // Logout
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/auth/login";
      }
    }

    return Promise.reject(error);
  }
);

// ─── TIPOS ────────────────────────────────────────────────────
export interface Property {
  id: string;
  source: string;
  external_id?: string;
  url: string;
  property_type: string;
  operation: string;
  status: string;
  title: string;
  price?: number;
  price_usd?: number;
  currency: string;
  price_per_m2_usd?: number;
  bedrooms?: number;
  bathrooms?: number;
  area_total?: number;
  neighborhood?: string;
  city: string;
  latitude?: number;
  longitude?: number;
  ai_score?: number;
  ai_premium: boolean;
  ai_opportunity: boolean;
  ai_undervalued: boolean;
  ai_tags?: string[];
  main_image_url?: string;
  created_at: string;
  first_seen_at?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface MarketStats {
  total_properties: number;
  active_properties: number;
  new_today: number;
  new_this_week: number;
  price_drops_this_week: number;
  avg_price_sale_usd?: number;
  avg_price_rent_usd?: number;
  avg_price_m2_usd?: number;
  by_type: Record<string, number>;
  by_zone: Record<string, number>;
  by_source: Record<string, number>;
  premium_count: number;
  opportunity_count: number;
}

// ─── API FUNCTIONS ─────────────────────────────────────────────
export const propertiesApi = {
  list: (params?: Record<string, any>) =>
    api.get<PaginatedResponse<Property>>("/properties/", { params }),

  get: (id: string) =>
    api.get<Property>(`/properties/${id}`),

  stats: (params?: Record<string, any>) =>
    api.get<MarketStats>("/properties/stats", { params }),

  opportunities: (limit = 20) =>
    api.get<Property[]>(`/properties/opportunities?limit=${limit}`),

  similar: (id: string, limit = 6) =>
    api.get<Property[]>(`/properties/${id}/similar?limit=${limit}`),

  priceHistory: (id: string) =>
    api.get(`/properties/${id}/price-history`),
};

export interface GroupPost {
  id: string;
  group_id: string;
  group_name?: string;
  permalink?: string;
  author_name?: string;
  external_links?: string[];
  text: string;
  kind: "oferta" | "demanda" | "otro";
  operation?: string;
  property_type?: string;
  period?: string;
  neighborhood?: string;
  price?: number;
  currency?: string;
  bedrooms?: number;
  contact_phone?: string;
  confidence: number;
  is_reviewed: boolean;
  posted_at?: string;
  created_at: string;
}

export const groupPostsApi = {
  list: (params?: Record<string, any>) =>
    api.get<PaginatedResponse<GroupPost>>("/group-posts", { params }),

  trigger: () => api.post("/group-posts/trigger"),
};

export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),

  register: (data: { email: string; password: string; full_name: string }) =>
    api.post("/auth/register", data),

  me: () => api.get("/auth/me"),
};

export const scrapingApi = {
  trigger: (sources?: string[]) =>
    api.post("/scraping/trigger", { sources }),

  runs: (params?: Record<string, any>) =>
    api.get("/scraping/runs", { params }),

  status: () => api.get("/scraping/status"),
};
