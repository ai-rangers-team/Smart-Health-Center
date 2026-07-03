import { useEffect, useRef, useState } from "react";
import { useLang } from "../i18n/translations";

/* Small shared atoms, ported 1:1 from the approved design system. */

const LANG_NAMES = { en: "English", hi: "हिंदी", mr: "मराठी" };

export function LanguageSwitch({ onDark = false }) {
  const { lang, setLang } = useLang();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex items-center gap-2 rounded-headerpill px-3 py-2 text-sm font-medium ${
          onDark
            ? "bg-white/10 text-white hover:bg-white/20"
            : "border border-line bg-surface text-ink hover:bg-line-light"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.7-3.8-9S9.5 5.6 12 3Z" />
        </svg>
        {LANG_NAMES[lang]}
        <svg
          viewBox="0 0 24 24"
          className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label="Language"
          className="absolute right-0 z-50 mt-1.5 w-40 rounded-tile border border-line bg-surface py-1 shadow-lg"
        >
          {Object.entries(LANG_NAMES).map(([code, name]) => (
            <li key={code}>
              <button
                type="button"
                role="option"
                aria-selected={lang === code}
                onClick={() => {
                  setLang(code);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between px-3.5 py-2.5 text-left text-sm hover:bg-line-lightest ${
                  lang === code ? "font-semibold text-brand" : "text-ink"
                }`}
              >
                {name}
                {lang === code && <span aria-hidden="true">✓</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
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
  high: "bg-status-warning-soft text-status-warning-deep",
  medium: "bg-status-warning-soft text-status-warning-deep",
  low: "bg-status-healthy-soft text-status-healthy-deep",
};

export function StatusBadge({ status, children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-chip px-3 py-1 text-xs font-semibold ${
        STATUS_STYLES[status] || STATUS_STYLES.healthy
      } ${className}`}
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

/**
 * Numeric −/+ stepper. The number itself is directly editable (numeric keypad
 * on phones) — steppers for small nudges, typing for big counts like stock.
 */
export function Stepper({ value, onChange, min = 0, big = false }) {
  const size = big ? "h-16 w-16 text-2xl" : "h-12 w-12 text-xl";
  const handleType = (e) => {
    const raw = e.target.value.replace(/[^\d]/g, "");
    onChange(raw === "" ? min : Math.max(min, parseInt(raw, 10)));
  };
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        aria-label="Decrease"
        onClick={() => onChange(Math.max(min, value - 1))}
        className={`${size} rounded-stepper border border-line-control bg-canvas font-bold text-ink`}
      >
        &minus;
      </button>
      <input
        value={value}
        onChange={handleType}
        onFocus={(e) => e.target.select()}
        inputMode="numeric"
        pattern="[0-9]*"
        aria-label="Count"
        className={`tabular w-20 rounded-stepper-sm border border-transparent bg-transparent text-center font-bold focus:border-line-control focus:bg-surface focus:outline-none ${
          big ? "text-4xl" : "text-2xl"
        }`}
      />
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

/** Reactive online/offline state (listens to browser events). */
export function useOnline() {
  const [online, setOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}
