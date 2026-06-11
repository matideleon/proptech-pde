"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Loader2 } from "lucide-react";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await authApi.login(email.trim(), password);
      localStorage.setItem("access_token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      router.push("/dashboard");
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || "No se pudo iniciar sesión. Revisá tus datos."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-6">
          <div className="h-12 w-12 rounded-xl bg-brand-500 flex items-center justify-center mb-3">
            <Building2 className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold">PropTech PDE</h1>
          <p className="text-sm text-muted-foreground">
            Inteligencia inmobiliaria · Punta del Este
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-card border rounded-xl p-6 shadow-card space-y-4"
        >
          <h2 className="font-semibold">Iniciar sesión</h2>

          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Email</label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@proptech.uy"
              className="w-full bg-background border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Contraseña</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-background border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 bg-red-500/10 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-500 text-white rounded-lg px-3 py-2.5 text-sm font-medium hover:bg-brand-600 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
