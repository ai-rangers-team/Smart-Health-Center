import { useEffect, useRef, useState } from "react";

/**
 * Progressive text reveal for AI-generated content — makes machine-written
 * text visually distinct from static UI copy. Adaptive speed (~1.2s for any
 * length), subtle caret while typing, instant when the user prefers reduced
 * motion, and re-animates only when the text itself changes.
 */
export default function Typewriter({ text = "", className = "" }) {
  const [shown, setShown] = useState(0);
  const prevText = useRef(null);

  useEffect(() => {
    if (text === prevText.current) return;
    prevText.current = text;

    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!text || reduced) {
      setShown(text.length);
      return;
    }

    setShown(0);
    const ticks = 70; // total animation ≈ 70 × 16ms ≈ 1.1s regardless of length
    const step = Math.max(1, Math.ceil(text.length / ticks));
    const iv = setInterval(() => {
      setShown((s) => {
        const next = s + step;
        if (next >= text.length) {
          clearInterval(iv);
          return text.length;
        }
        return next;
      });
    }, 16);
    return () => clearInterval(iv);
  }, [text]);

  const typing = shown < text.length;
  return (
    <span className={className}>
      {text.slice(0, shown)}
      {typing && <span className="animate-pulse font-light">▍</span>}
    </span>
  );
}
