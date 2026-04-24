import { useEffect } from "react";
import { X, Check, Warning } from "@phosphor-icons/react";

/**
 * Brutalist confirmation dialog for financial data verification.
 *
 * Props:
 *  - open: boolean
 *  - title: string (defaults to "Konfirmasi Data")
 *  - subtitle: string
 *  - rows: [{ label, value, accent?: "pos"|"neg"|"ink"|"yellow" }]
 *  - confirmLabel: string (default "Ya, Simpan")
 *  - cancelLabel: string (default "Batal")
 *  - onConfirm: () => void  (called synchronously, parent handles async)
 *  - onCancel: () => void
 *  - loading: boolean — when true, disables buttons and shows "MENYIMPAN…"
 *  - tone: "default" | "warning"
 */
export default function ConfirmDialog({
  open,
  title = "Konfirmasi Data",
  subtitle = "Pastikan data yang akan disimpan sudah benar.",
  rows = [],
  confirmLabel = "Ya, Simpan",
  cancelLabel = "Batal",
  onConfirm,
  onCancel,
  loading = false,
  tone = "default",
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape" && !loading) onCancel?.();
      if (e.key === "Enter" && !loading) onConfirm?.();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, loading, onCancel, onConfirm]);

  if (!open) return null;

  const accentClass = {
    pos: "text-pos",
    neg: "text-neg",
    yellow: "text-[var(--ink)]",
    ink: "text-[var(--ink)]",
  };

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center p-4" data-testid="confirm-dialog">
      <div
        className="absolute inset-0 bg-black/55 backdrop-blur-[2px]"
        onClick={() => !loading && onCancel?.()}
        data-testid="confirm-dialog-backdrop"
      />
      <div
        className="relative w-full max-w-md bg-white border-2 border-black shadow-[8px_8px_0_0_#0A0A0A] animate-[hero-pop_220ms_ease-out]"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b-2 border-black bg-[var(--brand-bg)]">
          <div className="flex items-start gap-3">
            <div className={`w-10 h-10 border-2 border-black flex items-center justify-center shrink-0 ${tone === "warning" ? "bg-[var(--neg)] text-white" : "bg-black text-[var(--brand-bg)]"}`}>
              {tone === "warning" ? <Warning size={20} weight="bold" /> : <Check size={20} weight="bold" />}
            </div>
            <div>
              <div className="overline font-bold">VERIFIKASI</div>
              <h3 className="font-display font-black text-xl tracking-tighter leading-tight mt-1" data-testid="confirm-dialog-title">{title}</h3>
            </div>
          </div>
          <button
            onClick={onCancel}
            disabled={loading}
            className="p-1 hover:bg-black hover:text-[var(--brand-bg)] border-2 border-transparent hover:border-black disabled:opacity-40"
            data-testid="confirm-dialog-close"
            aria-label="Tutup"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          <p className="text-sm text-[var(--ink-soft)] font-mono" data-testid="confirm-dialog-subtitle">{subtitle}</p>

          {rows.length > 0 && (
            <div className="border-2 border-black" data-testid="confirm-dialog-rows">
              {rows.map((r, i) => (
                <div
                  key={`${r.label}-${i}`}
                  className={`flex items-start justify-between gap-4 px-4 py-3 ${
                    i !== rows.length - 1 ? "border-b border-black/15" : ""
                  } ${i % 2 === 0 ? "bg-[var(--brand-bg-soft)]" : "bg-white"}`}
                  data-testid={`confirm-row-${i}`}
                >
                  <span className="overline font-bold">{r.label}</span>
                  <span className={`font-mono text-sm font-bold text-right break-words ${accentClass[r.accent] || "text-[var(--ink)]"}`}>
                    {r.value}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2 text-xs font-mono text-[var(--ink-soft)]">
            <span className="pulse-dot" /> TEKAN <kbd className="px-1.5 border border-black font-bold">ENTER</kbd> UNTUK SIMPAN · <kbd className="px-1.5 border border-black font-bold">ESC</kbd> UNTUK BATAL
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t-2 border-black flex flex-col-reverse sm:flex-row gap-3 sm:justify-end bg-[var(--brand-bg-soft)]">
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn-ghost flex items-center justify-center gap-2"
            data-testid="confirm-dialog-cancel"
          >
            <X size={14} /> {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="btn-ink flex items-center justify-center gap-2"
            data-testid="confirm-dialog-confirm"
          >
            <Check size={14} /> {loading ? "MENYIMPAN…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
