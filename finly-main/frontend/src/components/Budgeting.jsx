import { useCallback, useEffect, useState } from "react";
import { Plus, Trash, FloppyDisk, Coin } from "@phosphor-icons/react";
import api from "../services/api";
import { formatRupiah, currentMonth, monthLabel, stripDigits, OUTCOME_CATEGORIES } from "../services/utils";
import ConfirmDialog from "./ConfirmDialog";

export default function Budgeting() {
  const [month, setMonth] = useState(currentMonth());
  const [items, setItems] = useState([]);
  const [serverItems, setServerItems] = useState([]);
  const [totalBudget, setTotalBudget] = useState(0);
  const [totalReal, setTotalReal] = useState(0);
  const [capital, setCapital] = useState({ amount: "", description: "", exists: false });
  const [msg, setMsg] = useState(null);
  const [capMsg, setCapMsg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [confirm, setConfirm] = useState({ open: false, kind: null, saving: false, rowIndex: -1 });

  // BUG-12 + BUG-18
  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const d = await api.getBudgets(month);
      setServerItems(d.budgets || []);
      setItems(
        (d.budgets || [])
          .filter((b) => b.id)
          .map((b) => ({ id: b.id, category: b.category, amount: String(b.budget) }))
      );
      setTotalBudget(d.total_budget ?? 0);
      setTotalReal(d.total_realisasi ?? 0);
      const cap = d.monthly_capital;
      setCapital({
        amount: cap ? String(cap.amount) : "",
        description: cap?.description || "",
        exists: !!cap,
      });
    } catch (e) {
      setLoadError(e?.response?.data?.detail || "Gagal memuat data anggaran.");
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => { load(); }, [load]);

  const addRow = () => setItems([...items, { id: null, uid: `new-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, category: "", amount: "" }]);

  // BUG-06 + BUG-09: use ConfirmDialog and refresh server data after delete
  const rmRow = (i) => {
    const it = items[i];
    if (!it?.id) {
      setItems(items.filter((_, idx) => idx !== i));
      return;
    }
    setConfirm({ open: true, kind: "row-delete", saving: false, rowIndex: i });
  };

  const doRemoveRow = async () => {
    const i = confirm.rowIndex;
    const it = items[i];
    setConfirm((c) => ({ ...c, saving: true }));
    try {
      if (it?.id) await api.deleteBudget(it.id);
      await load();
      setMsg({ kind: "ok", text: "Baris anggaran dihapus." });
      setTimeout(() => setMsg(null), 2500);
    } catch (e) {
      setMsg({ kind: "err", text: e?.response?.data?.detail || "Gagal menghapus baris." });
    } finally {
      setConfirm({ open: false, kind: null, saving: false, rowIndex: -1 });
    }
  };

  const budgetPayload = items
    .filter((it) => it.category && it.amount)
    .map((it) => ({ category: it.category, amount: Number(it.amount) }));
  const budgetSum = budgetPayload.reduce((s, it) => s + it.amount, 0);

  const requestSaveBudget = () => {
    if (!budgetPayload.length) {
      setMsg({ kind: "err", text: "Tidak ada baris anggaran untuk disimpan." });
      return;
    }
    setConfirm({ open: true, kind: "budget", saving: false, rowIndex: -1 });
  };

  const doSaveBudget = async () => {
    setConfirm((c) => ({ ...c, saving: true }));
    try {
      await api.saveBudgets({ month, items: budgetPayload });
      setMsg({ kind: "ok", text: "Anggaran tersimpan." });
      load();
      setTimeout(() => setMsg(null), 2500);
    } catch (e) {
      setMsg({ kind: "err", text: e?.response?.data?.detail || "Gagal menyimpan." });
    } finally {
      setConfirm({ open: false, kind: null, saving: false, rowIndex: -1 });
    }
  };

  const requestSaveCapital = () => {
    if (!capital.amount || Number(capital.amount) < 0) {
      setCapMsg({ kind: "err", text: "Nominal modal awal harus ≥ 0." });
      return;
    }
    setConfirm({ open: true, kind: "capital", saving: false, rowIndex: -1 });
  };

  const doSaveCapital = async () => {
    setConfirm((c) => ({ ...c, saving: true }));
    try {
      await api.saveMonthlyCapital({
        month,
        amount: Number(capital.amount),
        description: capital.description,
      });
      setCapMsg({ kind: "ok", text: "Modal awal tersimpan." });
      load();
      setTimeout(() => setCapMsg(null), 2500);
    } catch (e) {
      setCapMsg({ kind: "err", text: e?.response?.data?.detail || "Gagal menyimpan." });
    } finally {
      setConfirm({ open: false, kind: null, saving: false, rowIndex: -1 });
    }
  };

  // BUG-09: replace window.confirm with ConfirmDialog
  const requestRemoveCapital = () => {
    setConfirm({ open: true, kind: "capital-delete", saving: false, rowIndex: -1 });
  };

  const doRemoveCapital = async () => {
    setConfirm((c) => ({ ...c, saving: true }));
    try {
      await api.deleteMonthlyCapital(month);
      setCapital({ amount: "", description: "", exists: false });
      setCapMsg({ kind: "ok", text: "Modal awal dihapus." });
      setTimeout(() => setCapMsg(null), 2500);
      load();
    } catch (e) {
      setCapMsg({ kind: "err", text: e?.response?.data?.detail || "Gagal menghapus." });
    } finally {
      setConfirm({ open: false, kind: null, saving: false, rowIndex: -1 });
    }
  };

  const setRow = (i, patch) => {
    const copy = [...items];
    copy[i] = { ...copy[i], ...patch };
    setItems(copy);
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6" data-testid="budgeting-page">
      <div className="page-hero flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="overline">MODUL 03 · ANGGARAN BULANAN</div>
          <h1 className="font-display font-black text-3xl sm:text-4xl lg:text-5xl tracking-tighter mt-2">Anggaran</h1>
          <p className="text-sm text-[var(--ink-soft)] mt-2 font-mono">{monthLabel(month)}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="overline">BULAN</label>
          <input type="month" className="input-brut input-mono max-w-[200px]" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="budget-month-picker" />
        </div>
      </div>

      {loadError && (
        <div className="brut-card p-4 border-[var(--neg)] bg-neg-soft text-neg font-mono text-sm" data-testid="budget-load-error">
          {loadError}
        </div>
      )}

      {/* Modal Awal Bulan */}
      <div className="brut-card p-6" data-testid="monthly-capital-card">
        <div className="flex items-start justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 border hairline-strong flex items-center justify-center shrink-0">
              <Coin size={20} weight="regular" />
            </div>
            <div>
              <div className="overline">MODAL AWAL BULAN</div>
              <div className="font-display font-bold text-xl tracking-tight mt-1">Pengeluaran di awal bulan</div>
              <p className="text-xs text-[var(--ink-soft)] mt-1 font-mono max-w-md">
                Nominal tetap yang dikeluarkan di awal bulan (mis. sewa tempat, stok awal, setoran modal). Otomatis ikut dihitung di Laba/Rugi Dashboard.
              </p>
            </div>
          </div>
          {capital.exists && (
            <span className="tag tag-outcome" data-testid="monthly-capital-exists-badge">TERCATAT</span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3 items-end">
          <div>
            <label className="label-brut">Nominal (Rp)</label>
            <div className="money-group">
              <span className="money-group__prefix">Rp</span>
              <input
                className="money-group__input"
                inputMode="numeric"
                placeholder="0"
                value={capital.amount ? Number(capital.amount).toLocaleString("id-ID") : ""}
                onChange={(e) => setCapital({ ...capital, amount: stripDigits(e.target.value) })}
                data-testid="monthly-capital-amount"
              />
            </div>
            {capital.amount && (
              <div className="ticker mt-1">{formatRupiah(capital.amount)}</div>
            )}
          </div>
          <div>
            <label className="label-brut">Keterangan (opsional)</label>
            <input
              className="input-brut"
              placeholder="Sewa tempat + stok awal"
              value={capital.description}
              onChange={(e) => setCapital({ ...capital, description: e.target.value })}
              data-testid="monthly-capital-description"
            />
          </div>
          <div className="flex gap-2 md:min-w-[220px]">
            <button onClick={requestSaveCapital} className="btn-ink flex items-center gap-2 flex-1 justify-center whitespace-nowrap" data-testid="monthly-capital-save">
              <FloppyDisk size={14} /> Simpan
            </button>
            {capital.exists && (
              <button onClick={requestRemoveCapital} className="btn-ghost !px-3 shrink-0" data-testid="monthly-capital-delete">
                <Trash size={14} />
              </button>
            )}
          </div>
        </div>

        {capMsg && (
          <div className={`mt-3 px-3 py-2 text-sm font-mono border ${capMsg.kind === "ok" ? "border-[var(--pos)] bg-pos-soft text-pos" : "border-[var(--neg)] bg-neg-soft text-neg"}`} data-testid="monthly-capital-message">
            {capMsg.text}
          </div>
        )}
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 stagger">
        <div className="kpi-yellow p-5" data-testid="budget-total-plan">
          <div className="overline">TOTAL ANGGARAN</div>
          <div className="kpi-value text-3xl mt-2">{formatRupiah(totalBudget)}</div>
        </div>
        <div className="brut-card p-5" data-testid="budget-total-real">
          <div className="overline">TOTAL REALISASI</div>
          <div className="kpi-value text-3xl mt-2 font-mono">{formatRupiah(totalReal)}</div>
        </div>
        <div className="kpi-yellow p-5" data-testid="budget-total-selisih">
          <div className="overline">SELISIH</div>
          <div className={`kpi-value text-3xl mt-2 ${totalBudget - totalReal >= 0 ? "text-pos" : "text-neg"}`}>
            {formatRupiah(totalBudget - totalReal)}
          </div>
        </div>
      </div>

      {/* Plan editor */}
      <div className="brut-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="overline">EDITOR ANGGARAN</div>
            <div className="font-display font-bold text-xl tracking-tight mt-1">Tetapkan plafon per kategori</div>
          </div>
          <div className="flex gap-2">
            <button onClick={addRow} className="btn-ghost flex items-center gap-2" data-testid="budget-add-row"><Plus size={14} /> Tambah Kategori</button>
            <button onClick={requestSaveBudget} className="btn-ink flex items-center gap-2" data-testid="budget-save"><FloppyDisk size={14} /> Simpan</button>
          </div>
        </div>

        {msg && (
          <div className={`px-3 py-2 text-sm font-mono border ${msg.kind === "ok" ? "border-[var(--pos)] bg-pos-soft text-pos" : "border-[var(--neg)] bg-neg-soft text-neg"}`} data-testid="budget-message">
            {msg.text}
          </div>
        )}

        <div className="overflow-x-auto scroll-custom">
          <table className="brut-table">
            <thead>
              <tr>
                <th>Kategori</th>
                <th style={{ width: 220 }}>Anggaran</th>
                <th style={{ width: 60 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr><td colSpan="3" className="text-center text-[var(--ink-soft)] font-mono py-6">Klik <b>Tambah Kategori</b> untuk mulai.</td></tr>
              )}
              {items.map((it, i) => (
                <tr key={it.id || it.uid || `row-${i}`}>
                  <td>
                    <input
                      list="cat-list"
                      className="input-brut"
                      value={it.category}
                      onChange={(e) => setRow(i, { category: e.target.value })}
                      placeholder="contoh: Marketing"
                      data-testid={`budget-cat-${i}`}
                    />
                    <datalist id="cat-list">
                      {OUTCOME_CATEGORIES.map((c) => <option key={c} value={c} />)}
                    </datalist>
                  </td>
                  <td>
                    <input
                      className="input-brut input-mono"
                      inputMode="numeric"
                      value={it.amount ? Number(it.amount).toLocaleString("id-ID") : ""}
                      onChange={(e) => setRow(i, { amount: stripDigits(e.target.value) })}
                      placeholder="0"
                      data-testid={`budget-amount-${i}`}
                    />
                  </td>
                  <td className="text-right">
                    <button onClick={() => rmRow(i)} className="p-1 hover:bg-neg-soft" data-testid={`budget-remove-${i}`}>
                      <Trash size={14} className="text-neg" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Realisasi table */}
      <div className="brut-card p-6" data-testid="budget-realisasi-table">
        <div className="overline">REALISASI vs ANGGARAN</div>
        <div className="font-display font-bold text-xl tracking-tight mt-1">Kinerja kategori</div>
        <div className="overflow-x-auto scroll-custom mt-4">
          <table className="brut-table">
            <thead>
              <tr>
                <th>Kategori</th>
                <th className="text-right">Anggaran</th>
                <th className="text-right">Realisasi</th>
                <th className="text-right">Selisih</th>
                <th style={{ width: 140 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="5" className="text-center font-mono py-6 text-[var(--ink-soft)]">Memuat…</td></tr>}
              {!loading && serverItems.length === 0 && (
                <tr><td colSpan="5" className="text-center font-mono py-6 text-[var(--ink-soft)]">Belum ada anggaran.</td></tr>
              )}
              {serverItems.map((b, i) => {
                const ratio = b.budget > 0 ? Math.min(1, b.realisasi / b.budget) : 1;
                const over = b.status === "over";
                return (
                  <tr key={b.category} data-testid={`budget-row-${b.category}`}>
                    <td className="font-medium">{b.category}</td>
                    <td className="font-mono text-right">{formatRupiah(b.budget)}</td>
                    <td className="font-mono text-right">{formatRupiah(b.realisasi)}</td>
                    <td className={`font-mono text-right ${b.selisih >= 0 ? "text-pos" : "text-neg"}`}>{formatRupiah(b.selisih)}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-black/10">
                          <div
                            className="h-full"
                            style={{ width: `${ratio * 100}%`, background: over ? "var(--neg)" : "var(--pos)" }}
                          />
                        </div>
                        <span className={`tag ${over ? "tag-outcome" : "tag-income"}`}>{over ? "OVER" : "OK"}</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={confirm.open}
        title={
          confirm.kind === "capital" ? "Simpan Modal Awal?" :
          confirm.kind === "capital-delete" ? "Hapus Modal Awal?" :
          confirm.kind === "row-delete" ? "Hapus Baris Anggaran?" :
          "Simpan Anggaran?"
        }
        subtitle={
          confirm.kind === "capital"
            ? "Modal awal akan tercatat sebagai pengeluaran di awal bulan dan ikut dihitung pada Laba/Rugi."
            : confirm.kind === "capital-delete"
            ? "Modal awal bulan ini akan dihapus dari perhitungan Laba/Rugi."
            : confirm.kind === "row-delete"
            ? "Kategori anggaran ini akan dihapus permanen dari bulan berjalan."
            : "Anggaran akan meng-upsert (menimpa) plafon per kategori pada bulan yang dipilih."
        }
        rows={
          confirm.kind === "capital"
            ? [
                { label: "Bulan", value: monthLabel(month) },
                { label: "Nominal", value: formatRupiah(capital.amount), accent: "neg" },
                { label: "Keterangan", value: capital.description || "—" },
              ]
            : confirm.kind === "capital-delete"
            ? [
                { label: "Bulan", value: monthLabel(month) },
                { label: "Nominal saat ini", value: formatRupiah(capital.amount), accent: "neg" },
              ]
            : confirm.kind === "row-delete"
            ? (() => {
                const it = items[confirm.rowIndex] || {};
                return [
                  { label: "Kategori", value: it.category || "—" },
                  { label: "Nominal", value: formatRupiah(it.amount || 0), accent: "neg" },
                ];
              })()
            : [
                { label: "Bulan", value: monthLabel(month) },
                { label: "Jumlah Kategori", value: `${budgetPayload.length} baris` },
                ...budgetPayload.slice(0, 5).map((it) => ({
                  label: it.category,
                  value: formatRupiah(it.amount),
                })),
                ...(budgetPayload.length > 5
                  ? [{ label: "…", value: `+${budgetPayload.length - 5} kategori lainnya` }]
                  : []),
                { label: "Total", value: formatRupiah(budgetSum), accent: "neg" },
              ]
        }
        confirmLabel={
          confirm.kind === "capital" ? "Ya, Simpan Modal Awal" :
          confirm.kind === "capital-delete" ? "Ya, Hapus Modal" :
          confirm.kind === "row-delete" ? "Ya, Hapus Baris" :
          "Ya, Simpan Anggaran"
        }
        onCancel={() => !confirm.saving && setConfirm({ open: false, kind: null, saving: false, rowIndex: -1 })}
        onConfirm={
          confirm.kind === "capital" ? doSaveCapital :
          confirm.kind === "capital-delete" ? doRemoveCapital :
          confirm.kind === "row-delete" ? doRemoveRow :
          doSaveBudget
        }
        loading={confirm.saving}
      />
    </div>
  );
}
