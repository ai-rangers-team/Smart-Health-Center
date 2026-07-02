import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useCollection, useDoc } from "../hooks/useFirestore";
import { useLang } from "../i18n/translations";
import { Choice2, LanguageSwitch, Stepper } from "../components/ui";

const TESTS = ["malaria", "tb", "pregnancy", "diabetes", "hiv"];

/**
 * PHC operator daily report — ported from the approved design (phone-first,
 * big steppers, plain language). Saves call the operator REST endpoints so the
 * backend recomputes forecasts + alerts on write (the live demo moment).
 * Staff attendance uses doctor/nurse counts per the API contract.
 */
export default function MyCentre() {
  const { centreId, signOut } = useAuth();
  const { t, lang } = useLang();

  const centre = useDoc(`centres/${centreId}`);
  const stockRows = useCollection(`centres/${centreId}/stock`);
  const bedsDoc = useDoc(`centres/${centreId}/beds/current`);
  const testsDoc = useDoc(`centres/${centreId}/tests/current`);

  const [patients, setPatients] = useState(0);
  const [bedsOccupied, setBedsOccupied] = useState(0);
  const [docsPresent, setDocsPresent] = useState(0);
  const [docsTotal, setDocsTotal] = useState(2);
  const [stock, setStock] = useState({});
  const [tests, setTests] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (bedsDoc) setBedsOccupied(bedsDoc.occupied || 0);
  }, [bedsDoc]);
  useEffect(() => {
    if (testsDoc) setTests(Object.fromEntries(TESTS.map((k) => [k, testsDoc[k] !== false])));
  }, [testsDoc]);
  useEffect(() => {
    setStock(Object.fromEntries(stockRows.map((m) => [m.id, m.current_stock ?? 0])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(stockRows.map((m) => m.id + ":" + m.current_stock))]);

  const online = typeof navigator !== "undefined" ? navigator.onLine : true;

  async function saveAll() {
    if (!centreId) return;
    setSaving(true);
    setError("");
    try {
      for (const m of stockRows) {
        if (stock[m.id] !== m.current_stock) {
          await api.patch(`/api/centres/${centreId}/stock`, {
            medicine_id: m.id,
            current_stock: stock[m.id],
          });
        }
      }
      await api.patch(`/api/centres/${centreId}/beds`, { occupied: bedsOccupied });
      await api.post(`/api/centres/${centreId}/footfall`, { count: patients });
      await api.post(`/api/centres/${centreId}/attendance`, {
        doctors_present: docsPresent,
        doctors_total: Math.max(docsTotal, 1),
      });
      await api.patch(`/api/centres/${centreId}/tests`, { tests });
      setSavedAt(new Date());
    } catch (e) {
      setError(e?.error || "Could not send the report. Check the connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-phone flex-col bg-canvas">
      <header className="rounded-b-card bg-brand-deep px-5 pb-4 pt-3 text-white">
        <div className="flex items-center justify-between">
          <LanguageSwitch onDark />
          <span className={`text-xs ${online ? "text-ondark-soft" : "text-status-warning"}`}>
            {online ? "●" : "○"} {online ? "" : t("no_network")}
          </span>
        </div>
        <div className="mt-2 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold">{centre?.name || "…"}</h1>
            <p className="text-sm text-ondark-subtle">
              {centre?.location?.block} ·{" "}
              {new Date().toLocaleDateString(lang === "en" ? "en-IN" : lang === "hi" ? "hi-IN" : "mr-IN", {
                weekday: "short",
                day: "numeric",
                month: "long",
              })}
            </p>
          </div>
          <button
            onClick={signOut}
            className="rounded-headerpill bg-white/10 px-3 py-1.5 text-sm font-medium"
          >
            {t("sign_out")}
          </button>
        </div>
      </header>

      <main className="flex-1 space-y-4 px-4 pb-32 pt-4">
        {savedAt && (
          <section className="rounded-card border border-status-healthy/30 bg-status-healthy-soft p-4">
            <p className="font-semibold text-status-healthy-deep">
              ✓ {online ? t("todays_report_sent") : t("saved_will_sync")}
            </p>
            <p className="mt-0.5 text-sm text-status-healthy-deep/80">
              {t("sent_at")}{" "}
              {savedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>
          </section>
        )}
        {error && (
          <section className="rounded-card bg-status-critical-soft p-4 text-sm font-medium text-status-critical">
            {error}
          </section>
        )}

        <section className="rounded-card border border-line bg-surface p-5">
          <h2 className="font-semibold">{t("patients_seen_today")}</h2>
          <div className="mt-4 flex justify-center">
            <Stepper value={patients} onChange={setPatients} big />
          </div>
        </section>

        <section className="rounded-card border border-line bg-surface p-5">
          <h2 className="font-semibold">{t("beds_section")}</h2>
          <p className="text-sm text-ink-muted">
            {bedsOccupied} {t("of")} {bedsDoc?.total ?? "—"}
          </p>
          <div className="mt-4 flex justify-center">
            <Stepper value={bedsOccupied} onChange={setBedsOccupied} />
          </div>
        </section>

        <section className="rounded-card border border-line bg-surface p-5">
          <h2 className="font-semibold">{t("staff_present_today")}</h2>
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm">
                {t("present")} ({t("staff_present")})
              </p>
              <Stepper value={docsPresent} onChange={setDocsPresent} />
            </div>
            <div className="flex items-center justify-between border-t border-line-light pt-3">
              <p className="text-sm text-ink-muted">{t("of")}</p>
              <Stepper value={docsTotal} onChange={setDocsTotal} min={1} />
            </div>
          </div>
        </section>

        <section className="rounded-card border border-line bg-surface p-5">
          <h2 className="font-semibold">{t("medicine_stock")}</h2>
          <p className="text-sm text-ink-muted">{t("how_much_left")}</p>
          <ul className="mt-4 space-y-5">
            {stockRows.map((m) => (
              <li key={m.id} className="border-b border-line-light pb-4 last:border-0 last:pb-0">
                <p className="font-medium">{m.medicine_name}</p>
                <p className="text-xs text-ink-faint">{m.unit}</p>
                <div className="mt-2 flex justify-center">
                  <Stepper
                    value={stock[m.id] ?? 0}
                    onChange={(v) => setStock((s) => ({ ...s, [m.id]: v }))}
                  />
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-card border border-line bg-surface p-5">
          <h2 className="font-semibold">{t("tests_section")}</h2>
          <ul className="mt-4 space-y-3">
            {TESTS.map((name) => (
              <li key={name} className="flex items-center justify-between">
                <p className="text-sm font-medium capitalize">{name}</p>
                <Choice2
                  value={tests[name]}
                  onChange={(v) => setTests((tt) => ({ ...tt, [name]: v }))}
                  onLabel={t("available")}
                  offLabel={t("not_available")}
                  danger
                />
              </li>
            ))}
          </ul>
        </section>
      </main>

      <div className="fixed inset-x-0 bottom-0 mx-auto max-w-phone bg-gradient-to-t from-canvas via-canvas to-transparent p-4">
        <button
          onClick={saveAll}
          disabled={saving}
          className="w-full rounded-card bg-brand py-4 text-lg font-semibold text-white disabled:opacity-60"
        >
          {saving ? "…" : t("save_send_report")}
        </button>
      </div>
    </div>
  );
}
