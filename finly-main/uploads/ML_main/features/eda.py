"""
eda.py — Exploratory Data Analysis
====================================
Output:
- Ringkasan statistik di terminal
- 4 grafik: distribusi, pola mingguan/bulanan, tren, korelasi
- eda_report.png (grafik disimpan otomatis)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
import warnings
warnings.filterwarnings('ignore')


# ─── Konfigurasi ─────────────────────────────────────────────────────────────

RAW_DATA_PATH = r"D:\Financial_Forecast\Data\Restaurant_source\RestaurantDataVets_All_2to5.csv"
OUTPUT_PATH   = r"D:\Financial_Forecast\src\features\eda_report.png"
# ==========================

TARGET_COLUMN = '2to5'
DATE_COLUMN   = 'DMY'
DROP_COLS     = ['Index', 'Group', 'MissingPrevDays']


# ─── Fungsi ──────────────────────────────────────────────────────────────────

def load_raw(file_path, date_column, drop_cols):
    df = pd.read_csv(file_path)
    df = df.replace('?', np.nan).dropna()
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.sort_values(date_column).dropna(subset=[date_column])
    df = df.set_index(date_column)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df = df.select_dtypes(include=[np.number])
    return df


def print_summary(df, target):
    print("=" * 55)
    print("           RINGKASAN DATASET")
    print("=" * 55)
    print(f"Total baris    : {len(df)}")
    print(f"Total fitur    : {len(df.columns)}")
    print(f"Periode        : {df.index.min().date()} s/d {df.index.max().date()}")
    print()
    print("=== Statistik Target (2to5) ===")
    desc = df[target].describe()
    print(f"  Mean   : {desc['mean']:>10.2f}")
    print(f"  Std    : {desc['std']:>10.2f}")
    print(f"  Min    : {desc['min']:>10.2f}")
    print(f"  Median : {desc['50%']:>10.2f}")
    print(f"  Max    : {desc['max']:>10.2f}")
    print()

    # Outlier check
    mean, std = df[target].mean(), df[target].std()
    outliers = df[target][df[target] > mean + 3 * std]
    print(f"=== Outlier (> mean + 3×std = {mean + 3*std:.0f}) ===")
    print(f"  Jumlah outlier : {len(outliers)}")
    if len(outliers) > 0:
        print(f"  Nilai tertinggi: {outliers.max():.2f} ({outliers.idxmax().date()})")
    print()

    # Korelasi tertinggi
    corr = df.corr()[target].drop(target).abs().sort_values(ascending=False)
    print("=== 10 Fitur Paling Berkorelasi dengan Target ===")
    for col, val in corr.head(10).items():
        bar = '█' * int(val * 20)
        print(f"  {col:<20} {val:.3f}  {bar}")
    print()

    # Pola hari dalam minggu
    df_r = df.reset_index()
    df_r['weekday'] = df_r[DATE_COLUMN].dt.day_name()
    weekly = df_r.groupby('weekday')[target].mean().reindex(
        ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    )
    print("=== Rata-rata Penjualan per Hari ===")
    for day, val in weekly.items():
        bar = '█' * int(val / 100)
        print(f"  {day:<12} {val:>8.1f}  {bar}")
    print()


def plot_eda(df, target, output_path):
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Exploratory Data Analysis — Restaurant Sales (2to5)',
                 fontsize=14, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

    # ── Plot 1: Tren penjualan sepanjang waktu ──
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df.index, df[target], color='steelblue', linewidth=0.8, alpha=0.8)
    # Rolling mean 30 hari
    rm30 = df[target].rolling(30).mean()
    ax1.plot(df.index, rm30, color='darkorange', linewidth=2, label='Rolling mean 30 hari')
    # Tandai outlier
    mean, std = df[target].mean(), df[target].std()
    outliers = df[target][df[target] > mean + 3 * std]
    ax1.scatter(outliers.index, outliers.values, color='red', s=40, zorder=5, label='Outlier')
    ax1.set_title('Tren Penjualan Harian (2016–2019)', fontweight='bold')
    ax1.set_xlabel('Tanggal')
    ax1.set_ylabel('Penjualan (2to5)')
    ax1.legend()
    ax1.grid(alpha=0.3)

    # ── Plot 2: Distribusi target ──
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.hist(df[target], bins=40, color='steelblue', edgecolor='white', alpha=0.8)
    ax2.axvline(mean,       color='darkorange', linewidth=2, linestyle='--', label=f'Mean: {mean:.0f}')
    ax2.axvline(df[target].median(), color='green', linewidth=2, linestyle='--',
                label=f'Median: {df[target].median():.0f}')
    ax2.axvline(mean + 3*std, color='red', linewidth=1.5, linestyle=':', label=f'Mean+3σ: {mean+3*std:.0f}')
    ax2.set_title('Distribusi Penjualan', fontweight='bold')
    ax2.set_xlabel('Nilai Penjualan (2to5)')
    ax2.set_ylabel('Frekuensi')
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    # ── Plot 3: Pola per hari dalam seminggu ──
    ax3 = fig.add_subplot(gs[1, 1])
    df_r = df.reset_index()
    df_r['weekday'] = df_r[DATE_COLUMN].dt.day_name()
    order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    weekly_mean = df_r.groupby('weekday')[target].mean().reindex(order)
    weekly_std  = df_r.groupby('weekday')[target].std().reindex(order)
    colors = ['#5B8DB8' if d not in ['Saturday','Sunday'] else '#E8A838' for d in order]
    bars = ax3.bar(range(7), weekly_mean.values, yerr=weekly_std.values,
                   color=colors, edgecolor='white', capsize=4, alpha=0.85)
    ax3.set_xticks(range(7))
    ax3.set_xticklabels(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
    ax3.set_title('Rata-rata Penjualan per Hari\n(oranye = akhir pekan)', fontweight='bold')
    ax3.set_ylabel('Penjualan (2to5)')
    for bar, val in zip(bars, weekly_mean.values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                 f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    ax3.grid(alpha=0.3, axis='y')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"Grafik EDA disimpan ke: {output_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = load_raw(RAW_DATA_PATH, DATE_COLUMN, DROP_COLS)
    print_summary(df, TARGET_COLUMN)
    plot_eda(df, TARGET_COLUMN, OUTPUT_PATH)
