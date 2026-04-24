import { useEffect, useState } from "react";
import Logo from "./Logo";

/**
 * Full-screen brand loading overlay for Finly.
 * Shows on first-paint / auth-check + can be used around async flows.
 *
 * Props:
 *  - label: string (small caption shown above the title)
 *  - minDuration: ms to show even if work finishes earlier (default 900)
 */
export default function LoadingScreen({ label = "MEMUAT", minDuration = 900 }) {
  const [progress, setProgress] = useState(0);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let raf;
    const start = performance.now();
    const step = (now) => {
      const elapsed = now - start;
      const p = Math.min(100, (elapsed / minDuration) * 100);
      setProgress(p);
      if (p < 100) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    const iv = setInterval(() => setTick((t) => (t + 1) % 4), 400);
    return () => { cancelAnimationFrame(raf); clearInterval(iv); };
  }, [minDuration]);

  return (
    <div
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center overflow-hidden"
      style={{ background: "var(--brand-bg)" }}
      data-testid="loading-screen"
      aria-busy="true"
    >
      {/* Animated background coins */}
      <div className="absolute inset-0 pointer-events-none">
        <span className="coin coin-a">$</span>
        <span className="coin coin-b">$</span>
        <span className="coin coin-c">$</span>
        <span className="coin coin-d">$</span>
        <span className="coin coin-e">$</span>
      </div>

      {/* Hero illustration */}
      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        <div className="loading-hero-wrap">
          <img
            src="/assets/finly-hero.png"
            alt="Finly financial growth"
            className="loading-hero"
            draggable="false"
          />
        </div>

        <div className="mt-6 text-[11px] font-mono tracking-[0.3em] text-black/60 uppercase" data-testid="loading-caption">
          {label}{".".repeat(tick)}
        </div>
        <div className="mt-3">
          <Logo size="xl" data-testid="loading-logo" />
        </div>
        <p className="mt-4 text-sm font-mono text-black/70 max-w-xs">
          Menyiapkan buku besar dan model prediksi Anda.
        </p>

        {/* Progress */}
        <div className="mt-6 w-64 sm:w-80 h-2 bg-white border-2 border-black" data-testid="loading-progress-bar">
          <div
            className="h-full bg-black transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mt-2 font-mono text-[10px] text-black/60">
          {Math.round(progress)}% · LSTM · LEDGER · SESSION
        </div>
      </div>

      {/* Corner labels */}
      <div className="absolute top-4 left-4 font-mono text-[10px] tracking-[0.2em] text-black/50" data-testid="loading-corner-left">FINLY · v1</div>
      <div className="absolute top-4 right-4 font-mono text-[10px] tracking-[0.2em] text-black/50" data-testid="loading-corner-right">IDR · ID-ID</div>
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 font-mono text-[10px] tracking-[0.2em] text-black/50">
        FOR YOUR FUTURE ·
      </div>
    </div>
  );
}
