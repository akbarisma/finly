export const formatRupiah = (amount) => {
  const n = Number(amount || 0);
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
};

export const formatShort = (amount) => {
  const n = Math.abs(Number(amount || 0));
  const sign = Number(amount || 0) < 0 ? "-" : "";
  if (n >= 1_000_000_000) return `${sign}Rp ${(n / 1_000_000_000).toFixed(1)}M`;
  if (n >= 1_000_000) return `${sign}Rp ${(n / 1_000_000).toFixed(1)}Jt`;
  if (n >= 1_000) return `${sign}Rp ${(n / 1_000).toFixed(0)}rb`;
  return `${sign}Rp ${n}`;
};

// BUG-16: cap digits to stay within Number.MAX_SAFE_INTEGER (~15 digits)
export const stripDigits = (s) => String(s).replace(/\D/g, "").slice(0, 15);

export const todayISO = () => {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

export const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

// BUG-03: parse ISO `YYYY-MM-DD` as local time to avoid off-by-one in +07:00
export const formatDateID = (iso) => {
  if (!iso) return "";
  const s = String(iso);
  const d = /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(s + "T00:00:00") : new Date(s);
  if (isNaN(d)) return "";
  return d.toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" });
};

export const formatDateTimeID = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const monthLabel = (ym) => {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("id-ID", { month: "long", year: "numeric" });
};

// BUG-10: actual last day of a YYYY-MM month (handles Feb/leap years)
export const lastDayOfMonth = (ym) => {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m, 0).getDate();
};

export const INCOME_CATEGORIES = ["Penjualan", "Jasa", "Investasi", "Lainnya"];
export const OUTCOME_CATEGORIES = [
  "Operasional",
  "Marketing",
  "Gaji",
  "Sewa",
  "Utilitas",
  "Bahan Baku",
  "Lainnya",
];
