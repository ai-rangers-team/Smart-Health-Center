import { useLang } from "../i18n/translations";

/* Small shared atoms, ported 1:1 from the approved design system. */

export function LanguageSwitch({ onDark = false }) {
  const { lang, setLang } = useLang();
  const base = "px-2.5 py-1 text-xs font-semibold rounded-seg transition-colors";
  return (
    <div
      className={`flex items-center gap-0.5 rounded-seg p-0.5 ${
        onDark ? "bg-white/10" : "bg-line-light"
      }`}
      role="group"
      aria-label="Language"
    >
      {["en", "hi", "mr"].map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`${base} ${
            lang === l
              ? "bg-white text-ink shadow-sm"
              : onDark
              ? "text-ondark-soft hover:text-white"
              : "text-ink-muted hover:text-ink"
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

const STATUS_STYLES = {
  critical: "bg-status-critical-soft text-status-critical",
  warning: "bg-status-warning-soft text-status-warning-deep",
  healthy: "bg-status-healthy-soft text-status-healthy-deep",
  operational: "bg-status-healthy-soft text-status-healthy-deep",
  underperforming: "bg-status-underperforming-soft text-status-underperforming-deep",
  under_resourced: "bg-status-underperforming-soft text-status-underperforming-deep",
  awaiting: "bg-status-warning-soft text-status-warning-deep",
};

export function StatusBadge({ status, children }) {
  return (
    <span
      className={`inline-flex items-center rounded-chip px-3 py-1 text-xs font-semibold ${
        STATUS_STYLES[status] || STATUS_STYLES.healthy
      }`}
    >
      {children}
    </span>
  );
}

/** Days-remaining depletion bar; color by urgency. */
export function DepletionBar({ daysRemaining, maxDays = 21 }) {
  const pct = Math.max(4, Math.min(100, (daysRemaining / maxDays) * 100));
  const color =
    daysRemaining <= 3
      ? "bg-status-critical"
      : daysRemaining <= 7
      ? "bg-status-warning"
      : "bg-status-healthy";
  return (
    <div className="h-1.5 w-full rounded-bar bg-line-track">
      <div className={`h-1.5 rounded-bar ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Big numeric −/+ stepper (primary 64px targets on mobile). */
export function Stepper({ value, onChange, min = 0, big = false }) {
  const size = big ? "h-16 w-16 text-2xl" : "h-12 w-12 text-xl";
  return (
    <div className="flex items-center gap-4">
      <button
        type="button"
        aria-label="Decrease"
        onClick={() => onChange(Math.max(min, value - 1))}
        className={`${size} rounded-stepper border border-line-control bg-canvas font-bold text-ink`}
      >
        &minus;
      </button>
      <span className={`tabular min-w-[3ch] text-center font-bold ${big ? "text-4xl" : "text-2xl"}`}>
        {value}
      </span>
      <button
        type="button"
        aria-label="Increase"
        onClick={() => onChange(value + 1)}
        className={`${size} rounded-stepper bg-brand font-bold text-white`}
      >
        +
      </button>
    </div>
  );
}

/** Two-state choice (Present/Absent, Available/Not available). */
export function Choice2({ value, onChange, onLabel, offLabel, danger = false }) {
  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={() => onChange(true)}
        aria-pressed={value === true}
        className={`rounded-action px-4 py-2.5 text-sm font-semibold ${
          value === true
            ? "bg-brand text-white"
            : "border border-line-control bg-canvas text-ink-muted"
        }`}
      >
        {onLabel}
      </button>
      <button
        type="button"
        onClick={() => onChange(false)}
        aria-pressed={value === false}
        className={`rounded-action px-4 py-2.5 text-sm font-semibold ${
          value === false
            ? danger
              ? "bg-status-critical text-white"
              : "border border-line-control bg-line-light text-ink"
            : "border border-line-control bg-canvas text-ink-muted"
        }`}
      >
        {offLabel}
      </button>
    </div>
  );
}

export function Monogram() {
  return (
    <div className="flex h-11 w-11 items-center justify-center rounded-headerpill bg-white text-sm font-bold text-brand-deep">
      SHC
    </div>
  );
}
