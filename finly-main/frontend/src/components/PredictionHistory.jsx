import { useCallback, useEffect, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { Eye, Trash, X, Cpu } from "@phosphor-icons/react";
import api from "../services/api";
import { formatRupiah, formatShort, formatDateTimeID, formatDateID } from "../services/utils";
import ConfirmDialog from "./ConfirmDialog";

export default function PredictionHistory() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  // BUG-09 + BUG-13: confirm state with explicit error handling
  const [confirm, setConfirm] = useState({ open: false, id: null, saving: false });
  const [toast, setToast] = useState(null);

  // BUG-11 + BUG-18
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.getPredictionHistory(page, 10);
      setItems(r.data || []);
      setTotal(r.total || 0);
    } catch {
      setError("Gagal memuat riwayat prediksi.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const open = async (id) => {
    setSelected(id);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const d = await api.getPredictionDetail(id);
      setDetail(d);
    } catch {
      setDetailError("Gagal memuat detail prediksi.");
    } finally {
      setDetailLoading(false);
    }
  };

  const close = () => { setSelected(null); setDetail(null); setDetailError(null); };

  const requestDelete = (id) => setConfirm({ open: true, id, saving: false });

  const doDelete = async () => {
    const id = confirm.id;
    setConfirm((c) => ({ ...c, saving: true }));
    try {
      await api.deletePrediction(id);
      if (selected === id) close();
      setToast({ kind: "ok", text: "Riwayat prediksi dihapus." });
      setTimeout(() => setToast(null), 2500);
      load();
    } catch (e) {
      setToast({ kind: "err", text: e?.response?.data?.detail || "Gagal menghapus prediksi." });
      setTimeout(() => setToast(null), 3000);
    } finally {
      setConfirm({ open: false, id: null, saving: false });
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / 10));

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6" data-testid="history-page">
      <div className="page-hero">
        <div className="overline">MODUL 06 · ARSIP</div>
        <h1 className="font-display font-black text-3xl sm:text-4xl lg:text-5xl tracking-tighter mt-2">Riwayat Prediksi</h1>
        <p className="text-sm text-[var(--ink-soft)] mt-2 font-mono">Semua forecast yang pernah dijalankan.</p>
      </div>

      <div className="brut-card">
        {error && (
          <div className="px-4 py-3 border-b hairline bg-neg-soft text-neg font-mono text-sm" data-testid="history-error">
            {error}
          </div>
        )}
        {toast && (
          <div className={`px-4 py-3 border-b hairline font-mono text-sm ${toast.kind === "ok" ? "bg-pos-soft text-pos" : "bg-neg-soft text-neg"}`} data-testid="history-toast">
            {toast.text}
          </div>
        )}
        <div className="overflow-x-auto scroll-custom">
          <table className="brut-table">
            <thead>
              <tr>
                <th style={{ width: 60 }}>#</th>
                <th>Dibuat</th>
                <th>Target Bulan</th>
                <th className="text-center">Horizon</th>
                <th className="text-right">Total</th>
                <th className="text-right">Rata-rata</th>
                <th style={{ width: 120 }}></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="7" className="text-center font-mono py-10 text-[var(--ink-soft)]">Memuat…</td></tr>}
              {!loading && items.length === 0 && (
                <tr><td colSpan="7" className="text-center font-mono py-10 text-[var(--ink-soft)]">Belum ada prediksi. Jalankan forecast di modul Prediksi ML.</td></tr>
              )}
              {!loading && items.map((it, i) => (
                <tr key={it.id} data-testid={`history-row-${it.id}`}>
                  <td className="font-mono text-xs text-[var(--ink-soft)]">{String((page - 1) * 10 + i + 1).padStart(2, "0")}</td>
                  <td className="font-mono text-sm">{formatDateTimeID(it.predicted_at)}</td>
                  <td className="font-mono text-sm">{it.month_target}</td>
                  <td className="text-center"><span className="tag">{it.n_days}D</span></td>
                  <td className="font-mono text-right font-semibold">{formatRupiah(it.total_predicted)}</td>
                  <td className="font-mono text-right">{formatShort(it.avg_daily)}</td>
                  <td className="text-right">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => open(it.id)} className="p-2 border hairline hover:bg-black hover:text-white transition-colors" data-testid={`history-view-${it.id}`}>
                        <Eye size={14} />
                      </button>
                      <button onClick={() => requestDelete(it.id)} className="p-2 border hairline hover:bg-neg-soft text-neg" data-testid={`history-delete-${it.id}`}>
                        <Trash size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t hairline">
          <div className="font-mono text-xs text-[var(--ink-soft)]">Hal. {page} dari {totalPages}</div>
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} data-testid="history-prev">Prev</button>
            <button className="btn-ghost" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} data-testid="history-next">Next</button>
          </div>
        </div>
      </div>

      {/* Drawer */}
      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end" data-testid="history-drawer">
          <div className="fixed inset-0 bg-black/60" onClick={close} />
          <div className="relative w-full max-w-2xl h-full bg-[var(--bg)] border-l hairline-strong overflow-y-auto scroll-custom">
            <div className="sticky top-0 bg-white border-b hairline-strong px-6 py-4 flex items-center justify-between z-10">
              <div className="flex items-center gap-3">
                <Cpu size={18} />
                <div>
                  <div className="overline">DETAIL PREDIKSI</div>
                  <div className="font-mono text-xs text-[var(--ink-soft)]">{detail ? formatDateTimeID(detail.predicted_at) : "…"}</div>
                </div>
              </div>
              <button onClick={close} className="p-2 hover:bg-black/5" data-testid="history-drawer-close"><X size={18} /></button>
            </div>
            {detailLoading && <div className="p-6 font-mono text-sm text-[var(--ink-soft)]">Memuat detail…</div>}
            {detailError && <div className="p-6 font-mono text-sm text-neg" data-testid="history-detail-error">{detailError}</div>}
            {detail && (
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-2 gap-3">
                  <div className="brut-card p-4"><div className="overline">HORIZON</div><div className="kpi-value text-2xl mt-1">{detail.n_days}D</div></div>
                  <div className="brut-card p-4"><div className="overline">TARGET</div><div className="kpi-value text-2xl mt-1 font-mono">{detail.month_target}</div></div>
                  <div className="brut-card p-4"><div className="overline">TOTAL</div><div className="kpi-value text-2xl mt-1 text-pos">{formatShort(detail.total_predicted)}</div></div>
                  <div className="brut-card p-4"><div className="overline">RATA-RATA</div><div className="kpi-value text-2xl mt-1">{formatShort(detail.avg_daily)}</div></div>
                </div>

                <div className="ml-panel p-5">
                  <div className="overline text-white/60">FORECAST SERIES</div>
                  <div className="h-[240px] mt-3">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={detail.detail_json.map((p) => ({ ...p, date: p.tanggal.slice(5) }))}>
                        <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fill: "#A3A3A3", fontFamily: "JetBrains Mono", fontSize: 10 }} stroke="#404040" />
                        <YAxis tick={{ fill: "#A3A3A3", fontFamily: "JetBrains Mono", fontSize: 10 }} stroke="#404040" tickFormatter={(v) => formatShort(v)} width={70} />
                        <Tooltip contentStyle={{ background: "#0A0A0A", border: "1px solid #7FB3FF", borderRadius: 0, fontFamily: "JetBrains Mono", fontSize: 12, color: "#E5E5E5" }} formatter={(v) => [formatRupiah(v), "Prediksi"]} />
                        <Line type="monotone" dataKey="prediksi" stroke="#7FB3FF" strokeWidth={2} dot={{ fill: "#7FB3FF", r: 2 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="brut-card">
                  <div className="px-5 py-4 border-b hairline"><div className="overline">TABEL LENGKAP</div></div>
                  <div className="max-h-[280px] overflow-y-auto scroll-custom">
                    <table className="brut-table">
                      <thead><tr><th>Tanggal</th><th>Hari</th><th className="text-right">Prediksi</th></tr></thead>
                      <tbody>
                        {detail.detail_json.map((p) => (
                          <tr key={p.tanggal}>
                            <td className="font-mono text-sm">{formatDateID(p.tanggal)}</td>
                            <td className="text-sm">{p.hari}</td>
                            <td className="font-mono text-right">{formatRupiah(p.prediksi)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirm.open}
        title="Hapus Riwayat Prediksi?"
        subtitle="Riwayat forecast ini akan dihapus permanen dan tidak bisa dikembalikan."
        rows={[]}
        confirmLabel="Ya, Hapus"
        onCancel={() => !confirm.saving && setConfirm({ open: false, id: null, saving: false })}
        onConfirm={doDelete}
        loading={confirm.saving}
      />
    </div>
  );
}
