import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../../services/api";
import { ArrowRight } from "@phosphor-icons/react";
import Logo from "../Logo";

function AuthShell({ children, titleTop, titleBottom, subtitle }) {
  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-[var(--brand-bg)]">
      {/* Left: yellow canvas with hero illustration */}
      <div className="relative lg:w-1/2 flex items-center justify-center p-6 sm:p-10 lg:p-12 overflow-hidden">
        {/* Floating coins */}
        <span className="coin coin-a hidden sm:grid">$</span>
        <span className="coin coin-b hidden sm:grid">$</span>
        <span className="coin coin-c hidden lg:grid">$</span>

        <div className="relative z-10 max-w-md w-full">
          <div className="flex items-center gap-3 mb-6 lg:mb-10">
            <Logo size="md" />
            <div>
              <div className="overline">FINANCIAL · EST 2026</div>
              <div className="text-[10px] font-mono text-[var(--ink-soft)] mt-1">LEDGER · LSTM</div>
            </div>
          </div>

          <div className="brut-card-solid p-4 bg-white mb-6 lg:mb-8 inline-block">
            <img
              src="/assets/finly-hero.png"
              alt="Finly"
              className="w-[240px] sm:w-[300px] lg:w-[360px] object-contain"
              draggable="false"
            />
          </div>

          <h1 className="font-display font-black text-4xl sm:text-5xl xl:text-6xl tracking-tighter leading-[0.95] text-black">
            {titleTop}
            <br />
            <span className="bg-black text-[var(--brand-bg)] px-2 inline-block">{titleBottom}</span>
          </h1>
          <p className="mt-5 text-sm text-black/75 max-w-md font-mono">{subtitle}</p>

          <div className="mt-6 lg:mt-10 hidden sm:flex items-center gap-4 lg:gap-6 text-[11px] font-mono text-black/60">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-[var(--pos)]" />LSTM FORECAST</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-[var(--neg)]" />IDR · ID-ID</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-black" />REALTIME</span>
          </div>
        </div>
      </div>

      {/* Right: white form panel */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12 bg-white border-t-2 lg:border-t-0 lg:border-l-2 hairline-strong">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit = form.email && form.password && !loading;

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setErr("");
    setLoading(true);
    try {
      const res = await api.login(form);
      localStorage.setItem("auth_token", res.token);
      localStorage.setItem("user_data", JSON.stringify(res.user));
      navigate("/");
    } catch (e2) {
      setErr(e2?.response?.data?.detail || "Email atau password salah.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      titleTop="Buku besar"
      titleBottom="keuanganmu."
      subtitle="Pencatatan, anggaran, dan prediksi LSTM — satu dasbor untuk tim finance UKM & startup."
    >
      <div className="space-y-8" data-testid="login-page">
        <div>
          <div className="overline">SESI · LOGIN</div>
          <h2 className="font-display font-black text-3xl tracking-tighter mt-2">Masuk ke Finly</h2>
          <p className="text-sm text-[var(--ink-soft)] mt-2">Lanjutkan pembukuan Anda.</p>
        </div>

        <form onSubmit={submit} className="space-y-5" data-testid="login-form">
          <div>
            <label className="label-brut" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              className="input-brut input-mono"
              placeholder="nama@usaha.co.id"
              data-testid="login-email-input"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="label-brut" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              className="input-brut input-mono"
              placeholder="••••••••"
              data-testid="login-password-input"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>

          {err && (
            <div className="border border-[var(--neg)] bg-neg-soft px-3 py-2 text-sm text-neg font-mono" data-testid="login-error">
              {err}
            </div>
          )}

          <button
            type="submit"
            className="btn-ink w-full flex items-center justify-center gap-2"
            disabled={!canSubmit}
            data-testid="login-submit-button"
          >
            {loading ? "Memproses…" : "Masuk"} <ArrowRight size={14} />
          </button>
        </form>

        <div className="border-t hairline pt-5 text-sm font-mono text-[var(--ink-soft)]">
          Belum punya akun?{" "}
          <Link to="/signup" className="text-[var(--ink)] underline underline-offset-4" data-testid="link-to-signup">
            Daftar di sini
          </Link>
        </div>
      </div>
    </AuthShell>
  );
}

export function SignUpPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", confirm: "", name: "" });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [ok, setOk] = useState(false);

  const validate = () => {
    const e = {};
    if (!form.email) e.email = "Email wajib diisi";
    else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) e.email = "Format email tidak valid";
    if (!form.password) e.password = "Password wajib diisi";
    else if (form.password.length < 8) e.password = "Password minimal 8 karakter";
    if (form.confirm !== form.password) e.confirm = "Konfirmasi tidak cocok";
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const v = validate();
    setErrors(v);
    if (Object.keys(v).length) return;
    setLoading(true);
    try {
      await api.register({ email: form.email, password: form.password, name: form.name || undefined });
      setOk(true);
      setTimeout(() => navigate("/login"), 1500);
    } catch (e2) {
      setErrors({ api: e2?.response?.data?.detail || "Gagal mendaftar. Coba lagi." });
    } finally {
      setLoading(false);
    }
  };

  const canSubmit = form.email && form.password && form.confirm && !loading;

  return (
    <AuthShell
      titleTop="Mulai"
      titleBottom="dari hari ini."
      subtitle="Bangun disiplin keuangan, lihat tren bulanan, dan prediksi penjualan dengan model LSTM."
    >
      <div className="space-y-8" data-testid="signup-page">
        <div>
          <div className="overline">SESI · DAFTAR</div>
          <h2 className="font-display font-black text-3xl tracking-tighter mt-2">Buat Akun Finly</h2>
          <p className="text-sm text-[var(--ink-soft)] mt-2">Gratis, tanpa kartu kredit.</p>
        </div>

        {ok ? (
          <div className="brut-card-solid p-6" data-testid="signup-success">
            <div className="overline text-pos">STATUS · 201 CREATED</div>
            <div className="font-display font-black text-2xl mt-2">Akun berhasil dibuat!</div>
            <div className="text-sm text-[var(--ink-soft)] mt-2 font-mono">Mengarahkan ke halaman login…</div>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5" data-testid="signup-form">
            <div>
              <label className="label-brut" htmlFor="su-name">Nama (opsional)</label>
              <input
                id="su-name"
                className="input-brut"
                placeholder="Budi Santoso"
                data-testid="signup-name-input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="label-brut" htmlFor="su-email">Email</label>
              <input
                id="su-email"
                type="email"
                className="input-brut input-mono"
                placeholder="nama@usaha.co.id"
                data-testid="signup-email-input"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              {errors.email && <div className="text-xs text-neg mt-1 font-mono" data-testid="signup-email-error">{errors.email}</div>}
            </div>
            <div>
              <label className="label-brut" htmlFor="su-pw">Password</label>
              <input
                id="su-pw"
                type="password"
                className="input-brut input-mono"
                placeholder="Minimal 8 karakter"
                data-testid="signup-password-input"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              {errors.password && <div className="text-xs text-neg mt-1 font-mono" data-testid="signup-password-error">{errors.password}</div>}
            </div>
            <div>
              <label className="label-brut" htmlFor="su-confirm">Konfirmasi Password</label>
              <input
                id="su-confirm"
                type="password"
                className="input-brut input-mono"
                data-testid="signup-confirm-input"
                value={form.confirm}
                onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              />
              {errors.confirm && <div className="text-xs text-neg mt-1 font-mono" data-testid="signup-confirm-error">{errors.confirm}</div>}
            </div>

            {errors.api && (
              <div className="border border-[var(--neg)] bg-neg-soft px-3 py-2 text-sm text-neg font-mono" data-testid="signup-api-error">
                {errors.api}
              </div>
            )}

            <button
              type="submit"
              className="btn-ink w-full flex items-center justify-center gap-2"
              disabled={!canSubmit}
              data-testid="signup-submit-button"
            >
              {loading ? "Membuat akun…" : "Daftar"} <ArrowRight size={14} />
            </button>
          </form>
        )}

        <div className="border-t hairline pt-5 text-sm font-mono text-[var(--ink-soft)]">
          Sudah punya akun?{" "}
          <Link to="/login" className="text-[var(--ink)] underline underline-offset-4" data-testid="link-to-login">
            Login di sini
          </Link>
        </div>
      </div>
    </AuthShell>
  );
}
