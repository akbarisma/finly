/**
 * Finly brand logo — reusable.
 * The source image has a black background with green letters, so we
 * embed it inside a black pill that matches our brutalist design.
 *
 * Props:
 *  - size: "xs" | "sm" | "md" | "lg" | "xl" (default: "md")
 *  - className: extra classes for the outer wrapper
 */
const SIZES = {
  xs: { h: "h-7", px: "px-2", img: "h-5" },
  sm: { h: "h-9", px: "px-2.5", img: "h-6" },
  md: { h: "h-11", px: "px-3", img: "h-8" },
  lg: { h: "h-16", px: "px-4", img: "h-12" },
  xl: { h: "h-24", px: "px-6", img: "h-20" },
};

export default function Logo({ size = "md", className = "", "data-testid": testid = "finly-logo" }) {
  const s = SIZES[size] || SIZES.md;
  return (
    <span
      className={`inline-flex items-center justify-center bg-black border-2 border-black ${s.h} ${s.px} ${className}`}
      data-testid={testid}
    >
      <img
        src="/assets/finly-logo.png"
        alt="Finly"
        className={`${s.img} w-auto object-contain select-none`}
        draggable="false"
      />
    </span>
  );
}
