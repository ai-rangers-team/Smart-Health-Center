import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useLang } from "../i18n/translations";
import { LanguageSwitch, Monogram } from "../components/ui";

// Demo gateway secret (production uses a strong SMS_WEBHOOK_SECRET sent by the real
// SMS/WhatsApp gateway, not this public page).
const SMS_SECRET = import.meta.env.VITE_SMS_SECRET || "demo-sms";

/**
 * Low-connectivity reporting: a feature-phone messaging the system. Types a short
 * stock text -> POST /api/sms/report -> the backend ACTUALLY writes the stock and
 * recomputes, so the district dashboard updates live. Same parser a production
 * SMS/WhatsApp gateway webhook would use. Public route: /sms-demo.
 */
export default function SmsDemo() {
  const { t } = useLang();
  const [params] = useSearchParams();
  const centreId = params.get("centre") || "phc_mulshi";
  const [text, setText] = useState("PARA 120 ORS 40 IFA 300");
  const [thread, setThread] = useState([]);
  const [busy, setBusy] = useState(false);

  async function send() {
    const msg = text.trim();
    if (!msg || busy) return;
    setBusy(true);
    setThread((th) => [...th, { from: "op", text: msg }]);
    setText("");
    try {
      const res = await api.post("/api/sms/report", {
        centre_id: centreId,
        text: msg,
        secret: SMS_SECRET,
      });
      let reply;
      if (res.applied?.length) {
        const items = res.applied.map((u) => `${u.medicine_name} ${u.current_stock}`).join(", ");
        reply = t("sms_reply_recorded", { centre: res.centre_name, items });
        if (res.unmatched?.length)
          reply += " " + t("sms_reply_unmatched", { names: res.unmatched.join(", ") });
      } else {
        reply = t("sms_reply_nothing");
      }
      setThread((th) => [...th, { from: "sys", text: reply }]);
    } catch {
      setThread((th) => [...th, { from: "sys", text: t("sms_reply_nothing") }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-phone flex-col bg-canvas">
      <header className="bg-brand-deep px-5 py-4 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Monogram />
            <span className="text-sm font-semibold">{t("app_name")}</span>
          </div>
          <LanguageSwitch onDark />
        </div>
      </header>

      <main className="flex-1 px-4 py-5">
        <h1 className="text-xl font-bold">{t("sms_title")}</h1>
        <p className="mt-1 text-sm text-ink-muted">{t("sms_sub")}</p>

        {/* Feature-phone chat frame */}
        <div className="mt-5 overflow-hidden rounded-card border border-line-control bg-surface shadow-sm">
          <div className="border-b border-line bg-line-lightest px-4 py-2 text-xs font-medium text-ink-muted">
            {t("sms_to")}
          </div>
          <div className="flex min-h-[220px] flex-col gap-2 p-4">
            {thread.length === 0 && (
              <p className="my-auto text-center text-sm text-ink-faint">
                {t("sms_placeholder")}
              </p>
            )}
            {thread.map((m, i) => (
              <div
                key={i}
                className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${
                  m.from === "op"
                    ? "self-end bg-brand text-white"
                    : "self-start bg-line-light text-ink"
                }`}
              >
                {m.text}
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 border-t border-line p-3">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder={t("sms_placeholder")}
              className="min-w-0 flex-1 rounded-action border border-line-control px-3 py-2 text-sm outline-none focus:border-brand"
            />
            <button
              onClick={send}
              disabled={busy}
              className="shrink-0 rounded-action bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-deep disabled:opacity-60"
            >
              {t("sms_send")}
            </button>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-ink-faint">{t("sms_hint")}</p>
      </main>
    </div>
  );
}
