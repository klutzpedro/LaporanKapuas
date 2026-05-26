import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiErrorDetail } from "@/lib/api";
import { ShieldStar, Lock, EnvelopeSimple } from "@phosphor-icons/react";
import { useNavigate } from "react-router-dom";

const QUICK = [
  { email: "admin@bais.tni.mil.id", pwd: "Bais2026!", label: "ADMIN" },
  { email: "piket@bais.tni.mil.id", pwd: "Piket2026!", label: "PIKET" },
  { email: "lid@bais.tni.mil.id", pwd: "Lid2026!", label: "LID" },
  { email: "kontra@bais.tni.mil.id", pwd: "Kontra2026!", label: "KONTRA" },
  { email: "gal@bais.tni.mil.id", pwd: "Gal2026!", label: "GAL" },
  { email: "medmon@bais.tni.mil.id", pwd: "Medmon2026!", label: "MEDMON" },
  { email: "geoint@bais.tni.mil.id", pwd: "Geoint2026!", label: "GEOINT" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@bais.tni.mil.id");
  const [password, setPassword] = useState("Bais2026!");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLogin(e) {
    e?.preventDefault?.();
    setBusy(true);
    setErr("");
    try {
      await login(email, password);
      nav("/");
    } catch (e2) {
      setErr(formatApiErrorDetail(e2.response?.data?.detail) || e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-stretch bg-zinc-950" data-testid="login-page">
      {/* Left: brand panel */}
      <div className="hidden md:flex md:w-1/2 grid-bg relative border-r border-zinc-800">
        <div className="absolute inset-0 bg-gradient-to-br from-zinc-950 via-zinc-950/80 to-transparent" />
        <div className="relative z-10 p-12 flex flex-col justify-between w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-500 text-zinc-950 flex items-center justify-center">
              <ShieldStar size={22} weight="fill" />
            </div>
            <div>
              <p className="overline">BAIS TNI</p>
              <h1 className="text-2xl font-black tracking-tighter uppercase">Geospasika</h1>
            </div>
          </div>
          <div>
            <p className="overline mb-3">CLASSIFIED // INTERNAL</p>
            <h2 className="text-5xl font-black uppercase leading-[0.95] tracking-tighter text-zinc-100">
              Summary<br />Harian<br /><span className="text-amber-500">Satgas Kapuas</span>
            </h2>
            <p className="mt-6 text-sm text-zinc-400 max-w-md leading-relaxed">
              Konsolidasi laporan harian dari Tim LID, KONTRA, GAL, MEDMON, GEOINT &amp; PIKET.
              Output: infografis &amp; summary 2 halaman PDF untuk pimpinan.
            </p>
          </div>
          <div className="flex gap-6 text-xs font-mono text-zinc-500">
            <span>v1.0</span>
            <span>•</span>
            <span>3 COG + INTERNASIONAL</span>
            <span>•</span>
            <span>AI ASSISTED</span>
          </div>
        </div>
      </div>

      {/* Right: form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="md:hidden mb-6 flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-500 text-zinc-950 flex items-center justify-center">
              <ShieldStar size={22} weight="fill" />
            </div>
            <div>
              <p className="overline">BAIS TNI</p>
              <h1 className="text-xl font-black uppercase tracking-tighter">Geospasika</h1>
            </div>
          </div>

          <p className="overline mb-2">SECURE LOGIN</p>
          <h2 className="text-3xl font-black uppercase tracking-tighter mb-1">Akses Terminal</h2>
          <p className="text-sm text-zinc-500 mb-8">Masukkan kredensial untuk melanjutkan.</p>

          <form onSubmit={handleLogin} className="space-y-5" data-testid="login-form">
            <div>
              <Label className="overline text-zinc-400">Email</Label>
              <div className="relative mt-2">
                <EnvelopeSimple size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <Input
                  data-testid="login-email-input"
                  type="email"
                  className="bg-zinc-900 border-zinc-800 pl-9 h-11 rounded-sm text-zinc-100 focus-visible:ring-amber-500/40 focus-visible:border-amber-500"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div>
              <Label className="overline text-zinc-400">Password</Label>
              <div className="relative mt-2">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <Input
                  data-testid="login-password-input"
                  type="password"
                  className="bg-zinc-900 border-zinc-800 pl-9 h-11 rounded-sm text-zinc-100 focus-visible:ring-amber-500/40 focus-visible:border-amber-500"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            {err && (
              <div data-testid="login-error" className="text-xs text-red-400 bg-red-950/30 border border-red-900/50 px-3 py-2 rounded-sm">
                {err}
              </div>
            )}

            <Button
              type="submit"
              disabled={busy}
              data-testid="login-submit-button"
              className="w-full h-11 rounded-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical"
            >
              {busy ? "MEMVERIFIKASI..." : "MASUK"}
            </Button>
          </form>

          <div className="mt-8 border-t border-zinc-800 pt-5">
            <p className="overline mb-3">Quick Login (Demo)</p>
            <div className="grid grid-cols-3 gap-2">
              {QUICK.map((q) => (
                <button
                  key={q.email}
                  type="button"
                  data-testid={`quick-login-${q.label.toLowerCase()}`}
                  onClick={() => { setEmail(q.email); setPassword(q.pwd); }}
                  className="text-[10px] font-mono uppercase tracking-wider py-1.5 px-2 border border-zinc-800 hover:border-amber-500/70 hover:text-amber-400 text-zinc-400 rounded-sm transition-colors"
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
