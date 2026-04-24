import { useCallback, useEffect, useState } from "react";
import { Plus, Trash, ArrowUpRight, ArrowDownRight } from "@phosphor-icons/react";
import api from "../services/api";
import {
  formatRupiah, stripDigits, todayISO, formatDateID,
  INCOME_CATEGORIES, OUTCOME_CATEGORIES,
} from "../services/utils";
import ConfirmDialog from "./ConfirmDialog";

const emptyForm = () => ({
  type: "income",
  category: "",
  amount: "",
  description: "",
  date: todayISO(),
});

export default function TransactionForm() {
  const [form, setForm] = useState(emptyForm());
  const [errors, setErrors] = useState({});
  const [msg, setMsg] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const categories = form.type === "income" ? INCOME_CATEGORIES : OUTCOME_CATEGORIES;

  const loadRecent = useCallback(async () => {
    try {
      const r = await api.getTransactions({ page: 1, limit: 8 });
      setRecent(r.data || []);
    } catch (e) {
      console.error("Gagal memuat transaksi terbaru:", e);
    }
  }, []);

  useEffect(() => { loadRecent(); }, [loadRecent]);

  const onAmount = (e) => setForm({ ...form, amount: stripDigits(e.target.value) });

  const validate = () => {
    const e = {};
    if (!form.category) e.category = "Kategori wajib dipilih";
    if (!form.amount || Number(form.amount) <= 0) e.amount = "Nominal harus lebih dari 0";
    if (!form.date) e.date = "Tanggal wajib diisi";
    return e;
  };

  // Opens confirm dialog after local validation
  const requestSave = (ev) => {
    ev.preventDefault();
    const v = validate();
    setErrors(v);
    if (Object.keys(v).length) return;
    setConfirmOpen(true);
  };

  // Actually submit after user confirms
  const confirmSave = async () => {
    setLoading(true);
    try {
      await api.addTransaction({
        type: form.type,
        category: form.category,
        amount: Number(form.amount),
        description: form.description || "",
        date: form.date,
      });
      setMsg({ kind: "ok", text: "Transaksi berhasil dicatat." });
      setForm({ ...emptyForm(), type: form.type });
      setConfirmOpen(false);
      loadRecent();
      setTimeout(() => setMsg(null), 2500);
    } catch (e2) {
      setMsg({ kind: "err", text: e2?.response?.data?.detail || "Gagal menyimpan." });
      setConfirmOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, tx: null, saving: false });

  const requestDelete = (tx) => setDeleteConfirm({ open: true, tx, saving: false });

  const doDelete = async () => {
    if (!deleteConfirm.tx) return;
    setDeleteConfirm((c) => ({ ...c, saving: true }));
    try {
      await api.deleteTransaction(deleteConfirm.tx.id);
      await loadRecent();
    } catch (e) {
      console.error("Gagal menghapus transaksi:", e);
    }
    finally {
      setDeleteConfirm({ open: false, tx: null, saving: false });
    }
  };

  const setType = (t) => setForm({ ...form, type: t, category: "" });

  const confirmRows = [
    { label: "Jenis", value: form.type === "income" ? "Pemasukan" : "Pengeluaran", accent: form.type === "income" ? "pos" : "neg" },
    { label: "Kategori", value: form.category || "—" },
    { label: "Nominal", value: formatRupiah(form.amount), accent: form.type === "income" ? "pos" : "neg" },
    { label: "Tanggal", value: formatDateID(form.date) },
    { label: "Deskripsi", value: form.description || "—" },
  ];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6" data-testid="transaksi-page">
      <div className="page-hero">
        <div className="overline">MODUL 02 · PENCATATAN</div>
        <h1 className="font-display font-black text-3xl sm:text-4xl lg:text-5xl tracking-tighter mt-2">Transaksi</h1>
        <p className="text-sm text-[var(--ink-soft)] mt-2 font-mono">Catat pemasukan & pengeluaran harian.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* FORM */}
        <form onSubmit={requestSave} className="brut-card p-6 lg:col-span-2 space-y-5" data-testid="tx-form">
          <div>
            <div className="label-brut">Jenis</div>
            <div className="grid grid-cols-2 gap-0 border hairline-strong">
              <button
                type="button"
                onClick={() => setType("income")}
                data-testid="tx-type-income"
                className={`flex items-center justify-center gap-2 py-3 font-semibold text-sm transition-colors ${
                  form.type === "income" ? "bg-[var(--pos)] text-white" : "bg-white hover:bg-black/5"
                }`}
              >
                <ArrowUpRight size={16} /> Pemasukan
              </button>
              <button
                type="button"
                onClick={() => setType("outcome")}
                data-testid="tx-type-outcome"
                className={`flex items-center justify-center gap-2 py-3 font-semibold text-sm border-l hairline-strong transition-colors ${
                  form.type === "outcome" ? "bg-[var(--neg)] text-white" : "bg-white hover:bg-black/5"
                }`}
              >
                <ArrowDownRight size={16} /> Pengeluaran
              </button>
            </div>
          </div>

          <div>
            <label className="label-brut">Kategori</label>
            <select
              className="input-brut"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              data-testid="tx-category-select"
            >
              <option value="">— Pilih kategori —</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            {errors.category && <div className="text-xs text-neg mt-1 font-mono">{errors.category}</div>}
          </div>

          <div>
            <label className="label-brut">Nominal (Rp)</label>
            <div className="money-group">
              <span className="money-group__prefix">Rp</span>
              <input
                className="money-group__input"
                placeholder="0"
                inputMode="numeric"
                value={form.amount ? Number(form.amount).toLocaleString("id-ID") : ""}
                onChange={onAmount}
                data-testid="tx-amount-input"
              />
            </div>
            {form.amount && (
              <div className="ticker mt-1">{formatRupiah(form.amount)}</div>
            )}
            {errors.amount && <div className="text-xs text-neg mt-1 font-mono">{errors.amount}</div>}
          </div>

          <div>
            <label className="label-brut">Tanggal</label>
            <input
              type="date"
              className="input-brut input-mono"
              value={form.date}
              max={todayISO()}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              data-testid="tx-date-input"
            />
            {errors.date && <div className="text-xs text-neg mt-1 font-mono">{errors.date}</div>}
          </div>

          <div>
            <label className="label-brut">Deskripsi (opsional)</label>
            <textarea
              className="input-brut resize-none"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Invoice, nota, atau catatan…"
              data-testid="tx-description-input"
            />
          </div>

          {msg && (
            <div
              className={`px-3 py-2 text-sm font-mono border ${
                msg.kind === "ok" ? "border-[var(--pos)] bg-pos-soft text-pos" : "border-[var(--neg)] bg-neg-soft text-neg"
              }`}
              data-testid="tx-message"
            >
              {msg.text}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-ink w-full flex items-center justify-center gap-2" data-testid="tx-submit">
            <Plus size={14} /> {loading ? "Menyimpan…" : "Simpan Transaksi"}
          </button>
        </form>

        {/* RECENT */}
        <div className="brut-card p-6 lg:col-span-3" data-testid="tx-recent">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="overline">LOG · 8 TERBARU</div>
              <div className="font-display font-bold text-xl tracking-tight mt-1">Transaksi terakhir</div>
            </div>
          </div>
          <div className="overflow-x-auto scroll-custom">
            <table className="brut-table">
              <thead>
                <tr>
                  <th style={{ width: 110 }}>Tanggal</th>
                  <th style={{ width: 90 }}>Jenis</th>
                  <th>Kategori</th>
                  <th>Deskripsi</th>
                  <th className="text-right">Nominal</th>
                  <th style={{ width: 60 }}></th>
                </tr>
              </thead>
              <tbody>
                {recent.length === 0 && (
                  <tr><td colSpan="6" className="text-center text-[var(--ink-soft)] font-mono py-8">Belum ada transaksi.</td></tr>
                )}
                {recent.map((t) => (
                  <tr key={t.id} data-testid={`tx-row-${t.id}`}>
                    <td className="font-mono text-sm">{formatDateID(t.date)}</td>
                    <td><span className={t.type === "income" ? "tag tag-income" : "tag tag-outcome"}>{t.type === "income" ? "IN" : "OUT"}</span></td>
                    <td className="text-sm">{t.category}</td>
                    <td className="text-sm text-[var(--ink-soft)] truncate max-w-[200px]">{t.description || "—"}</td>
                    <td className={`font-mono text-right font-semibold ${t.type === "income" ? "text-pos" : "text-neg"}`}>
                      {t.type === "income" ? "+" : "−"}{formatRupiah(t.amount)}
                    </td>
                    <td className="text-right">
                      <button onClick={() => requestDelete(t)} className="p-1 hover:bg-neg-soft" data-testid={`tx-delete-${t.id}`}>
                        <Trash size={14} className="text-neg" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="Simpan Transaksi?"
        subtitle="Periksa ulang detail di bawah sebelum data keuangan disimpan ke buku besar."
        rows={confirmRows}
        confirmLabel="Ya, Simpan Transaksi"
        onCancel={() => !loading && setConfirmOpen(false)}
        onConfirm={confirmSave}
        loading={loading}
      />

      <ConfirmDialog
        open={deleteConfirm.open}
        title="Hapus Transaksi?"
        subtitle="Baris ini akan dihapus permanen dari buku besar."
        rows={
          deleteConfirm.tx
            ? [
                { label: "Tanggal", value: formatDateID(deleteConfirm.tx.date) },
                { label: "Jenis", value: deleteConfirm.tx.type === "income" ? "Pemasukan" : "Pengeluaran", accent: deleteConfirm.tx.type === "income" ? "pos" : "neg" },
                { label: "Kategori", value: deleteConfirm.tx.category },
                { label: "Nominal", value: formatRupiah(deleteConfirm.tx.amount), accent: deleteConfirm.tx.type === "income" ? "pos" : "neg" },
              ]
            : []
        }
        confirmLabel="Ya, Hapus"
        onCancel={() => !deleteConfirm.saving && setDeleteConfirm({ open: false, tx: null, saving: false })}
        onConfirm={doDelete}
        loading={deleteConfirm.saving}
      />
    </div>
  );
}
