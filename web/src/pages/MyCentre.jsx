import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useCollection, useDoc } from "../hooks/useFirestore";
import { useLang } from "../i18n/translations";
import { Choice2, LanguageSwitch, Stepper, useOnline } from "../components/ui";

const TESTS = ["malaria", "tb", "pregnancy", "diabetes", "hiv"];

/**
 * PHC operator daily report. Responsive: single column on phones, two-column
 * grid on larger screens (same compact sections, never a stretched phone strip).
 * Saves call the operator REST endpoints so the backend recomputes forecasts +
 * alerts on write (the live demo moment).
 */
export default function MyCentre() {
  const { centreId, signOut } = useAuth();
  const { t, lang, local, hasChosenLang, setLang } = useLang();
  const online = useOnline();

  const centre = useDoc(`centres/${centreId}`);
  const stockRows = useCollection(`centres/${centreId}/stock`);
  const bedsDoc = useDoc(`centres/${centreId}/beds/current`);
  const testsDoc = useDoc(`centres/${centreId}/tests/current`);
  // Today's already-reported values (UTC date key, same as the backend writes)
  const todayKey = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const todayFootfall = useDoc(`centres/${centreId}/footfall/${todayKey}`);
  const todayAttendance = useDoc(`centres/${centreId}/attendance/${todayKey}`);

  // One-time regional default: only applies if the operator hasn't already
  // chosen a language, and never re-fires once they have.
  useEffect(() => {
    if (!hasChosenLang && centre?.default_language) setLang(centre.default_language);
  }, [hasChosenLang, centre?.default_language]);

  const [patients, setPatients] = useState(0);
  const [bedsOccupied, setBedsOccupied] = useState(0);
  const [bedsTotal, setBedsTotal] = useState(0);
  const [docsPresent, setDocsPresent] = useState(0);
  const [docsTotal, setDocsTotal] = useState(2);
  const [stock, setStock] = useState({});
  const [tests, setTests] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(null); // {at, patients, docsPresent, docsTotal, bedsOccupied}
  const [error, setError] = useState("");

  useEffect(() => {
    if (bedsDoc) {
      setBedsOccupied(bedsDoc.occupied || 0);
      setBedsTotal(bedsDoc.total || 0);
    }
  }, [bedsDoc]);
  // Prefill today's report if it was already sent — editing, not re-entering
  useEffect(() => {
    if (todayFootfall) setPatients(todayFootfall.count || 0);
  }, [todayFootfall]);
  useEffect(() => {
    if (todayAttendance) {
      setDocsPresent(todayAttendance.doctors_present || 0);
      setDocsTotal(todayAttendance.doctors_total || 2);
    }
  }, [todayAttendance]);
  useEffect(() => {
    if (testsDoc)
      setTests(Object.fromEntries(TESTS.map((k) => [k, testsDoc[k] !== false])));
  }, [testsDoc]);
  useEffect(() => {
    setStock(Object.fromEntries(stockRows.map((m) => [m.id, m.current_stock ?? 0])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(stockRows.map((m) => m.id + ":" + m.current_stock))]);

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
      await api.patch(`/api/centres/${centreId}/beds`, {
        occupied: bedsOccupied,
        total: bedsTotal,
      });
      await api.post(`/api/centres/${centreId}/footfall`, { count: patients });
      await api.post(`/api/centres/${centreId}/attendance`, {
        doctors_present: docsPresent,
        doctors_total: Math.max(docsTotal, 1),
      });
      await api.patch(`/api/centres/${centreId}/tests`, { tests });
      setSaved({
        at: new Date(),
        patients,
        docsPresent,
        docsTotal,
        bedsOccupied,
        bedsTotal,
      });
    } catch (e) {
      setError(
        e?.error || "Could not send the report. Check the connection and try again."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-phone flex-col bg-canvas md:max-w-4xl">
      <header className="bg-brand-deep px-5 pb-4 pt-3 text-white md:rounded-b-card">
        <div className="flex items-center justify-between">
          <LanguageSwitch onDark />
          <span
            className={`text-xs font-medium ${
              online ? "text-ondark-soft" : "text-status-warning"
            }`}
          >
            {online ? "●" : `○ ${t("no_network")}`}
          </span>
        </div>
        <div className="mt-2 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold">{centre?.name || "…"}</h1>
            <p className="text-sm text-ondark-subtle">
              {centre?.location?.block} ·{" "}
              {new Date().toLocaleDateString(
                lang === "en" ? "en-IN" : lang === "hi" ? "hi-IN" : "mr-IN",
                { weekday: "short", day: "numeric", month: "long" }
              )}
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

      <main className="flex-1 px-4 pb-32 pt-4">
        {saved && (
          <section className="mb-4 rounded-card border border-status-healthy/30 bg-status-healthy-soft p-4">
            <p className="font-semibold text-status-healthy-deep">
              ✓ {online ? t("todays_report_sent") : t("saved_will_sync")}
            </p>
            <p className="mt-0.5 text-sm text-status-healthy-deep/80">
              {t("sent_at")}{" "}
              {saved.at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>
            <div className="mt-3 flex gap-6 border-t border-status-healthy/20 pt-3">
              <div>
                <p className="tabular text-xl font-bold text-status-healthy-deep">
                  {saved.patients}
                </p>
                <p className="text-xs text-status-healthy-deep/70">
                  {t("patients_seen_today")}
                </p>
              </div>
              <div>
                <p className="tabular text-xl font-bold text-status-healthy-deep">
                  {saved.docsPresent}/{saved.docsTotal}
                </p>
                <p className="text-xs text-status-healthy-deep/70">{t("staff_present")}</p>
              </div>
              <div>
                <p className="tabular text-xl font-bold text-status-healthy-deep">
                  {saved.bedsOccupied}
                  {saved.bedsTotal ? `/${saved.bedsTotal}` : ""}
                </p>
                <p className="text-xs text-status-healthy-deep/70">{t("beds_section")}</p>
              </div>
            </div>
          </section>
        )}
        {error && (
          <section className="mb-4 rounded-card bg-status-critical-soft p-4 text-sm font-medium text-status-critical">
            {error}
          </section>
        )}

        <div className="grid gap-4 md:grid-cols-2 md:items-start">
          {/* Left column: counts */}
          <div className="space-y-4">
            <section className="rounded-card border border-line bg-surface p-5">
              <h2 className="font-semibold">{t("patients_seen_today")}</h2>
              <div className="mt-4 flex justify-center">
                <Stepper value={patients} onChange={setPatients} big />
              </div>
            </section>

            <section className="rounded-card border border-line bg-surface p-5">
              <h2 className="font-semibold">{t("beds_section")}</h2>
              <p className="text-sm text-ink-muted">
                {bedsOccupied} {t("of")} {bedsTotal}
              </p>
              <div className="mt-4 space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm">{t("occupied_label")}</p>
                  <Stepper value={bedsOccupied} onChange={setBedsOccupied} />
                </div>
                <div className="flex items-center justify-between gap-3 border-t border-line-light pt-3">
                  <p className="text-sm text-ink-muted">{t("total_beds_label")}</p>
                  <Stepper value={bedsTotal} onChange={setBedsTotal} />
                </div>
              </div>
            </section>

            <section className="rounded-card border border-line bg-surface p-5">
              <h2 className="font-semibold">{t("staff_present_today")}</h2>
              <div className="mt-4 space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm">{t("doctors_present_label")}</p>
                  <Stepper value={docsPresent} onChange={setDocsPresent} />
                </div>
                <div className="flex items-center justify-between gap-3 border-t border-line-light pt-3">
                  <p className="text-sm text-ink-muted">{t("total_doctors_label")}</p>
                  <Stepper value={docsTotal} onChange={setDocsTotal} min={1} />
                </div>
              </div>
            </section>

            <section className="rounded-card border border-line bg-surface p-5">
              <h2 className="font-semibold">{t("tests_section")}</h2>
              <ul className="mt-4 space-y-3">
                {TESTS.map((name) => (
                  <li key={name} className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium capitalize">{local("tests", name)}</p>
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
          </div>

          {/* Right column: medicines */}
          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("medicine_stock")}</h2>
            <p className="text-sm text-ink-muted">{t("how_much_left")}</p>
            <ul className="mt-4 space-y-5">
              {stockRows.map((m) => (
                <li
                  key={m.id}
                  className="border-b border-line-light pb-4 last:border-0 last:pb-0"
                >
                  <div className="flex items-baseline justify-between">
                    <p className="font-medium">
                      {m.medicine_name}
                      {local("meds", m.medicine_name) !== m.medicine_name && (
                        <span className="ml-2 text-xs font-normal text-ink-muted">
                          {local("meds", m.medicine_name)}
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-ink-faint">{local("units", m.unit)}</p>
                  </div>
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
        </div>
      </main>

      <div className="fixed inset-x-0 bottom-0 mx-auto w-full max-w-phone bg-gradient-to-t from-canvas via-canvas to-transparent p-4 md:max-w-4xl">
        <button
          onClick={saveAll}
          disabled={saving}
          className="w-full rounded-card bg-brand py-4 text-lg font-semibold text-white hover:bg-brand-deep disabled:opacity-60"
        >
          {saving ? "…" : t("save_send_report")}
        </button>
      </div>
    </div>
  );
}
