import { useEffect, useState } from "react";
import { Cpu, Lightning, Warning, CircleDashed } from "@phosphor-icons/react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import api from "../services/api";
import { formatRupiah, formatShort, formatDateID } from "../services/utils";

const PRESETS = [7, 14, 30];
const HARI_ID = {
  Monday: "Senin", Tuesday: "Selasa", Wednesday: "Rabu", Thursday: "Kamis",
  Friday: "Jumat", Saturday: "Sabtu", Sunday: "Minggu",
};

export default function Prediction() {
  const [nDays, setNDays] = useState(30);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [mlOk, setMlOk] = useState(null);

  useEffect(() => {
    api.mlHealth()
      .then((h) => setMlOk(h.status === "ok"))
      .catch(() => setMlOk(false));
  }, []);

  const run = async () => {
    setLoading(true); setErr(""); setResult(null);
    try {
      const r = await api.predict(nDays);
      setResult(r);
    } catch (e) {
      setErr(e?.response?.data?.detail || "ML service sedang tidak tersedia.");
    } finally {
      setLoading(false);
    }
  };

  const chartData = (result?.predictions || []).map((p) => ({
    date: p.tanggal.slice(5),
    prediksi: p.prediksi,
    label: p.tanggal,
  }));

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6" data-testid="prediksi-page">
      <div className="page-hero flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="overline">MODUL 05 · INTELIJEN</div>
          <h1 className="font-display font-black text-3xl sm:text-4xl lg:text-5xl tracking-tighter mt-2">Prediksi ML</h1>
          <p className="text-sm text-[var(--ink-soft)] mt-2 font-mono">LSTM forecasting — hasil inverse-scaled dari model pre-trained.</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <CircleDashed size={10} weight="fill" className={mlOk ? "text-pos blink-dot" : "text-neg"} />
          <span className="text-[var(--ink-soft)]">ML STATUS</span>
          <span className={mlOk ? "text-pos" : "text-neg"}>{mlOk == null ? "…" : mlOk ? "ONLINE" : "OFFLINE"}</span>
        </div>
      </div>

      {/* Control panel */}
      <div className="ml-panel p-6 relative z-10" data-testid="prediksi-control">
        <div className="flex items-center gap-2 relative z-10">
          <Cpu size={18} weight="regular" className="ml-accent" />
          <span className="overline text-white/60">FINLY·LSTM · v1 · TIMESTEP=14 · FEATURES=39</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mt-5 relative z-10">
          <div className="lg:col-span-3">
            <div className="ml-text text-sm mb-3">HORIZON · {nDays} HARI</div>
            <div className="flex items-center gap-2 mb-3">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => setNDays(p)}
                  data-testid={`prediksi-preset-${p}`}
                  className={`font-mono text-xs px-3 py-1.5 border transition-all ${
                    nDays === p
                      ? "bg-white text-black border-white"
                      : "bg-transparent text-white/80 border-white/30 hover:bg-white/10"
                  }`}
                >{p}D</button>
              ))}
            </div>
            <input
              type="range"
              min="1"
              max="90"
              value={nDays}
              onChange={(e) => setNDays(parseInt(e.target.value))}
              className="w-full accent-white"
              data-testid="prediksi-slider"
            />
            <div className="flex justify-between text-[10px] font-mono text-white/50 mt-1">
              <span>1</span><span>30</span><span>60</span><span>90</span>
            </div>
          </div>
          <div className="lg:col-span-2 flex items-end">
            <button
              onClick={run}
              disabled={loading}
              className="w-full font-mono text-sm py-3 bg-white text-black hover:bg-[#7FB3FF] transition-colors flex items-center justify-center gap-2 disabled:opacity-40"
              data-testid="prediksi-run"
            >
              <Lightning size={16} weight="fill" />
              {loading ? "FORECASTING…" : "RUN FORECAST"}
            </button>
          </div>
        </div>

        {err && (
          <div className="mt-4 border border-[#E11D48] bg-[#E11D48]/15 px-3 py-2 text-sm font-mono text-[#FECACA] flex items-center gap-2 relative z-10" data-testid="prediksi-error">
            <Warning size={14} /> {err}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger">
            <div className="ml-panel p-5 relative">
              <div className="overline text-white/60 relative z-10">TOTAL PREDIKSI</div>
              <div className="kpi-value text-3xl ml-glow mt-2 relative z-10" data-testid="prediksi-total">{formatShort(result.summary.total)}</div>
              <div className="text-xs font-mono text-white/50 mt-1 relative z-10">{formatRupiah(result.summary.total)}</div>
            </div>
            <div className="ml-panel p-5 relative">
              <div className="overline text-white/60 relative z-10">RATA-RATA / HARI</div>
              <div className="kpi-value text-3xl ml-glow mt-2 relative z-10" data-testid="prediksi-avg">{formatShort(result.summary.rata_rata)}</div>
              <div className="text-xs font-mono text-white/50 mt-1 relative z-10">{formatRupiah(result.summary.rata_rata)}</div>
            </div>
            <div className="ml-panel p-5 relative">
              <div className="overline text-white/60 relative z-10">MIN HARIAN</div>
              <div className="kpi-value text-3xl ml-glow mt-2 relative z-10" data-testid="prediksi-min">{formatShort(result.summary.minimum)}</div>
            </div>
            <div className="ml-panel p-5 relative">
              <div className="overline text-white/60 relative z-10">MAX HARIAN</div>
              <div className="kpi-value text-3xl ml-glow mt-2 relative z-10" data-testid="prediksi-max">{formatShort(result.summary.maksimum)}</div>
            </div>
          </div>

          {!result.used_user_data && (
            <div className="brut-card p-4 border-[var(--ink)] font-mono text-xs flex items-start gap-2" data-testid="prediksi-warning-no-data">
              <Warning size={16} className="shrink-0 mt-0.5" />
              Belum ada transaksi pemasukan dalam 90 hari terakhir. Prediksi dihasilkan dari pola model dasar (restaurant sales)
              — tambahkan transaksi untuk hasil yang lebih relevan.
            </div>
          )}

          <div className="ml-panel p-6" data-testid="prediksi-chart">
            <div className="overline text-white/60">FORECAST SERIES · {nDays} DAYS</div>
            <div className="h-[320px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "#A3A3A3", fontFamily: "JetBrains Mono", fontSize: 10 }} stroke="#404040" />
                  <YAxis tick={{ fill: "#A3A3A3", fontFamily: "JetBrains Mono", fontSize: 10 }} stroke="#404040" tickFormatter={(v) => formatShort(v)} width={70} />
                  <Tooltip
                    contentStyle={{ background: "#0A0A0A", border: "1px solid #7FB3FF", borderRadius: 0, fontFamily: "JetBrains Mono", fontSize: 12, color: "#E5E5E5" }}
                    formatter={(v) => [formatRupiah(v), "Prediksi"]}
                  />
                  <Line type="monotone" dataKey="prediksi" stroke="#7FB3FF" strokeWidth={2} dot={{ fill: "#7FB3FF", r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="brut-card" data-testid="prediksi-table">
            <div className="px-6 py-5 border-b hairline">
              <div className="overline">TABEL FORECAST · HARIAN</div>
              <div className="font-display font-bold text-xl tracking-tight mt-1">Proyeksi {nDays} hari ke depan</div>
            </div>
            <div className="overflow-x-auto scroll-custom max-h-[420px]">
              <table className="brut-table">
                <thead className="sticky top-0 bg-white z-10">
                  <tr>
                    <th style={{ width: 50 }}>#</th>
                    <th style={{ width: 160 }}>Tanggal</th>
                    <th>Hari</th>
                    <th className="text-right">Prediksi</th>
                  </tr>
                </thead>
                <tbody>
                  {result.predictions.map((p, i) => (
                    <tr key={p.tanggal} data-testid={`prediksi-row-${i}`}>
                      <td className="font-mono text-xs text-[var(--ink-soft)]">{String(i + 1).padStart(2, "0")}</td>
                      <td className="font-mono text-sm">{formatDateID(p.tanggal)}</td>
                      <td className="text-sm">{HARI_ID[p.hari] || p.hari}</td>
                      <td className="font-mono text-right font-semibold">{formatRupiah(p.prediksi)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="text-xs font-mono text-[var(--ink-soft)] text-center" data-testid="prediksi-saved-hint">
            Hasil prediksi otomatis tersimpan ke <b className="text-[var(--ink)]">Riwayat Prediksi</b>.
          </div>
        </>
      )}
    </div>
  );
}
