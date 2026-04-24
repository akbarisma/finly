import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { formatRupiah, formatDateID, monthLabel } from "./utils";

// Brutalist palette (matches app)
const COLORS = {
  ink: [10, 10, 10],
  brand: [253, 224, 71], // yellow
  pos: [5, 150, 105],
  neg: [225, 29, 72],
  soft: [82, 82, 82],
  hair: [230, 230, 230],
};

const PAGE = { w: 210, h: 297, margin: 15 };
const CONTENT_W = PAGE.w - PAGE.margin * 2;

function drawHeader(doc, { month, userName }) {
  const { margin } = PAGE;
  // Top black stripe
  doc.setFillColor(...COLORS.ink);
  doc.rect(0, 0, PAGE.w, 6, "F");

  // Logo box
  doc.setFillColor(...COLORS.brand);
  doc.setDrawColor(...COLORS.ink);
  doc.setLineWidth(0.6);
  doc.rect(margin, 12, 32, 12, "FD");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(...COLORS.ink);
  doc.text("FINLY", margin + 4, 20.5);

  // Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.text("Laporan Keuangan Bulanan", margin + 38, 19);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(...COLORS.soft);
  doc.text(`${monthLabel(month)} · Periode ${month}`, margin + 38, 25);

  if (userName) {
    doc.setFontSize(9);
    doc.text(`Untuk: ${userName}`, PAGE.w - margin, 19, { align: "right" });
    const now = new Date();
    const stamp = now.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
    doc.text(`Dicetak: ${stamp}`, PAGE.w - margin, 25, { align: "right" });
  }

  // Underline
  doc.setDrawColor(...COLORS.ink);
  doc.setLineWidth(0.8);
  doc.line(margin, 30, PAGE.w - margin, 30);
}

function drawKpiGrid(doc, dash, yStart) {
  const { margin } = PAGE;
  const gap = 4;
  const cardW = (CONTENT_W - gap) / 2;
  const cardH = 24;

  const cards = [
    { label: "TOTAL PENDAPATAN", value: formatRupiah(dash.revenue || 0), color: COLORS.pos, variant: "yellow" },
    { label: "TOTAL PENGELUARAN", value: formatRupiah(dash.total_expense || 0), color: COLORS.neg, variant: "white" },
    { label: "LABA / RUGI", value: formatRupiah(dash.profit_loss || 0), color: (dash.profit_loss || 0) >= 0 ? COLORS.pos : COLORS.neg, variant: "yellow" },
    { label: "JUMLAH TRANSAKSI", value: String(dash.transaction_count || 0), color: COLORS.ink, variant: "white" },
  ];

  cards.forEach((c, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = margin + col * (cardW + gap);
    const y = yStart + row * (cardH + gap);
    if (c.variant === "yellow") doc.setFillColor(...COLORS.brand);
    else doc.setFillColor(255, 255, 255);
    doc.setDrawColor(...COLORS.ink);
    doc.setLineWidth(0.6);
    doc.rect(x, y, cardW, cardH, "FD");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(...COLORS.soft);
    doc.text(c.label, x + 4, y + 6);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.setTextColor(...c.color);
    doc.text(c.value, x + 4, y + 17);
  });

  return yStart + 2 * (cardH + gap);
}

function drawBreakdown(doc, dash, yStart) {
  const { margin } = PAGE;
  const rowH = 7;
  const items = [
    { k: "Transaksi Pengeluaran", v: dash.outcome || 0 },
    { k: "Anggaran Terencana", v: dash.budget_total || 0 },
    { k: "Modal Awal Bulan", v: dash.monthly_capital || 0 },
  ];
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(...COLORS.ink);
  doc.text("Rincian Pengeluaran", margin, yStart);
  let y = yStart + 4;
  doc.setDrawColor(...COLORS.hair);
  doc.setLineWidth(0.3);
  items.forEach((it) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(...COLORS.soft);
    doc.text(it.k, margin, y + 5);
    doc.setTextColor(...COLORS.ink);
    doc.setFont("helvetica", "bold");
    doc.text(formatRupiah(it.v), PAGE.w - margin, y + 5, { align: "right" });
    doc.line(margin, y + 6.5, PAGE.w - margin, y + 6.5);
    y += rowH;
  });
  return y + 2;
}

function drawDailyChart(doc, daily, yStart) {
  const { margin } = PAGE;
  const chartH = 42;
  const chartY = yStart + 8;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(...COLORS.ink);
  doc.text("Arus Harian — Pendapatan vs Pengeluaran", margin, yStart + 4);

  // Legend
  doc.setFillColor(...COLORS.pos);
  doc.rect(PAGE.w - margin - 50, yStart, 3, 3, "F");
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(...COLORS.soft);
  doc.text("Pendapatan", PAGE.w - margin - 45, yStart + 2.6);
  doc.setFillColor(...COLORS.neg);
  doc.rect(PAGE.w - margin - 22, yStart, 3, 3, "F");
  doc.text("Pengeluaran", PAGE.w - margin - 17, yStart + 2.6);

  // Frame
  doc.setDrawColor(...COLORS.ink);
  doc.setLineWidth(0.4);
  doc.rect(margin, chartY, CONTENT_W, chartH);

  if (!daily || daily.length === 0) {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...COLORS.soft);
    doc.text("Belum ada transaksi di periode ini.", margin + CONTENT_W / 2, chartY + chartH / 2, { align: "center" });
    return chartY + chartH + 4;
  }

  const maxV = Math.max(1, ...daily.map((d) => Math.max(d.income || 0, d.outcome || 0)));
  const n = daily.length;
  const slotW = CONTENT_W / n;
  const barW = Math.min(3, slotW / 3);
  const gap = 0.3;

  daily.forEach((d, i) => {
    const xCenter = margin + slotW * (i + 0.5);
    const inc = d.income || 0;
    const out = d.outcome || 0;
    const hInc = (inc / maxV) * (chartH - 4);
    const hOut = (out / maxV) * (chartH - 4);
    // income bar left
    doc.setFillColor(...COLORS.pos);
    doc.rect(xCenter - barW - gap, chartY + chartH - hInc - 1, barW, hInc, "F");
    // outcome bar right
    doc.setFillColor(...COLORS.neg);
    doc.rect(xCenter + gap, chartY + chartH - hOut - 1, barW, hOut, "F");
  });

  // X axis labels (every 5th day)
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.setTextColor(...COLORS.soft);
  daily.forEach((d, i) => {
    if (i === 0 || i === n - 1 || (i + 1) % 5 === 0) {
      const xCenter = margin + slotW * (i + 0.5);
      const label = (d.date || "").slice(-2);
      doc.text(label, xCenter, chartY + chartH + 3.5, { align: "center" });
    }
  });

  return chartY + chartH + 8;
}

function drawCategoryChart(doc, cats, yStart) {
  const { margin } = PAGE;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(...COLORS.ink);
  doc.text("Top Pos Pengeluaran", margin, yStart + 4);

  let y = yStart + 9;
  if (!cats || cats.length === 0) {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(...COLORS.soft);
    doc.text("Belum ada data kategori.", margin, y + 4);
    return y + 8;
  }

  const top = cats.slice(0, 6);
  const maxV = Math.max(1, ...top.map((c) => c.amount || 0));
  const rowH = 7;
  const labelW = 45;
  const valueW = 38;
  const barMaxW = CONTENT_W - labelW - valueW - 4;

  top.forEach((c) => {
    const ratio = (c.amount || 0) / maxV;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(...COLORS.ink);
    doc.text(String(c.category || "—").slice(0, 22), margin, y + 4.5);
    // bar track
    doc.setFillColor(245, 245, 245);
    doc.rect(margin + labelW, y + 1, barMaxW, rowH - 2, "F");
    // bar value
    doc.setFillColor(...COLORS.ink);
    doc.rect(margin + labelW, y + 1, barMaxW * ratio, rowH - 2, "F");
    // value
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(...COLORS.ink);
    doc.text(formatRupiah(c.amount || 0), PAGE.w - margin, y + 4.5, { align: "right" });
    y += rowH;
  });
  return y + 2;
}

function drawFooter(doc) {
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setDrawColor(...COLORS.hair);
    doc.setLineWidth(0.3);
    doc.line(PAGE.margin, PAGE.h - 10, PAGE.w - PAGE.margin, PAGE.h - 10);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...COLORS.soft);
    doc.text("Finly · Financial Analyst", PAGE.margin, PAGE.h - 6);
    doc.text(`Halaman ${i} / ${pageCount}`, PAGE.w - PAGE.margin, PAGE.h - 6, { align: "right" });
  }
}

function ensureSpace(doc, y, needed) {
  if (y + needed > PAGE.h - 15) {
    doc.addPage();
    return PAGE.margin + 5;
  }
  return y;
}

export async function exportMonthlyReportPDF({ month, dashboard, transactions, budgets, capital, userName }) {
  const doc = new jsPDF({ unit: "mm", format: "a4", orientation: "portrait" });

  // PAGE 1: header + KPI + breakdown + charts
  drawHeader(doc, { month, userName });
  let y = 36;
  y = drawKpiGrid(doc, dashboard, y);
  y += 4;
  y = drawBreakdown(doc, dashboard, y);
  y += 4;
  y = drawDailyChart(doc, dashboard.daily_chart || [], y);
  y = ensureSpace(doc, y, 70);
  y = drawCategoryChart(doc, dashboard.category_chart || [], y);

  // Modal Awal (if exists)
  if (capital && capital.amount) {
    y = ensureSpace(doc, y, 20);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(...COLORS.ink);
    doc.text("Modal Awal Bulan", PAGE.margin, y + 4);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(...COLORS.soft);
    doc.text(`Nominal: ${formatRupiah(capital.amount)}`, PAGE.margin, y + 10);
    if (capital.description) doc.text(`Keterangan: ${capital.description}`, PAGE.margin, y + 15);
    y += capital.description ? 20 : 14;
  }

  // Budget vs Realisasi
  if (budgets && budgets.length) {
    y = ensureSpace(doc, y, 30);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(...COLORS.ink);
    doc.text("Anggaran vs Realisasi", PAGE.margin, y + 4);
    autoTable(doc, {
      startY: y + 7,
      margin: { left: PAGE.margin, right: PAGE.margin },
      head: [["Kategori", "Anggaran", "Realisasi", "Selisih", "Status"]],
      body: budgets.map((b) => [
        b.category,
        formatRupiah(b.budget),
        formatRupiah(b.realisasi),
        formatRupiah(b.selisih),
        (b.status || "").toUpperCase(),
      ]),
      styles: { font: "helvetica", fontSize: 9, cellPadding: 2, lineColor: COLORS.ink, lineWidth: 0.2 },
      headStyles: { fillColor: COLORS.ink, textColor: 255, fontStyle: "bold" },
      columnStyles: {
        1: { halign: "right" }, 2: { halign: "right" }, 3: { halign: "right" }, 4: { halign: "center" },
      },
      didParseCell: (data) => {
        if (data.section === "body" && data.column.index === 4) {
          const st = String(data.cell.raw || "").toLowerCase();
          if (st === "over") data.cell.styles.textColor = COLORS.neg;
          else data.cell.styles.textColor = COLORS.pos;
        }
      },
    });
    y = doc.lastAutoTable.finalY + 4;
  }

  // Transactions table — new page if needed
  if (transactions && transactions.length) {
    y = ensureSpace(doc, y, 30);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(...COLORS.ink);
    doc.text(`Daftar Transaksi (${transactions.length} entri)`, PAGE.margin, y + 4);
    autoTable(doc, {
      startY: y + 7,
      margin: { left: PAGE.margin, right: PAGE.margin },
      head: [["Tanggal", "Jenis", "Kategori", "Deskripsi", "Nominal"]],
      body: transactions.map((t) => [
        formatDateID(t.date),
        t.type === "income" ? "IN" : "OUT",
        t.category,
        t.description || "—",
        `${t.type === "income" ? "+" : "−"}${formatRupiah(t.amount)}`,
      ]),
      styles: { font: "helvetica", fontSize: 8.5, cellPadding: 1.8, lineColor: COLORS.ink, lineWidth: 0.15, overflow: "linebreak" },
      headStyles: { fillColor: COLORS.ink, textColor: 255, fontStyle: "bold" },
      columnStyles: {
        0: { cellWidth: 24 },
        1: { cellWidth: 13, halign: "center" },
        2: { cellWidth: 32 },
        3: { cellWidth: "auto" },
        4: { halign: "right", cellWidth: 32 },
      },
      didParseCell: (data) => {
        if (data.section === "body" && data.column.index === 4) {
          const raw = String(data.cell.raw || "");
          if (raw.startsWith("+")) data.cell.styles.textColor = COLORS.pos;
          else if (raw.startsWith("−") || raw.startsWith("-")) data.cell.styles.textColor = COLORS.neg;
        }
        if (data.section === "body" && data.column.index === 1) {
          const raw = String(data.cell.raw || "");
          data.cell.styles.textColor = raw === "IN" ? COLORS.pos : COLORS.neg;
          data.cell.styles.fontStyle = "bold";
        }
      },
    });
  }

  drawFooter(doc);
  doc.save(`Finly_Laporan_${month}.pdf`);
}
