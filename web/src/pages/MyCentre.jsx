import { useEffect, useRef, useState } from "react";
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
  const [extracting, setExtracting] = useState(false);
  const [invoiceReview, setInvoiceReview] = useState(null); // {unmatched: [names]}
  const [invoiceError, setInvoiceError] = useState("");
  const [recording, setRecording] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [voiceReview, setVoiceReview] = useState(null); // {transcript, unmatched}
  const [voiceError, setVoiceError] = useState("");
  const mediaRef = useRef(null); // { recorder, stream }
  const voiceSupported =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined";

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

  async function handleInvoiceFile(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file || !centreId) return;
    setExtracting(true);
    setInvoiceError("");
    setInvoiceReview(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post(`/api/centres/${centreId}/stock/extract`, form);
      setStock((s) => {
        const next = { ...s };
        for (const item of res.items || []) next[item.medicine_id] = item.proposed_stock;
        return next;
      });
      setInvoiceReview({ unmatched: res.unmatched || [] });
    } catch (e) {
      setInvoiceError(e?.detail || e?.error || t("invoice_extract_failed"));
    } finally {
      setExtracting(false);
    }
  }

  // Voice stock entry: record → send audio → Gemini transcribes + maps to catalog →
  // pre-fill the steppers for review (never writes; operator still taps Save).
  async function sendVoice(blob) {
    if (!centreId) return;
    setVoiceBusy(true);
    try {
      const form = new FormData();
      const ext = ((blob.type.split("/")[1] || "webm").split(";")[0]) || "webm";
      form.append("file", blob, `report.${ext}`);
      const res = await api.post(`/api/centres/${centreId}/stock/voice?lang=${lang}`, form);
      setStock((s) => {
        const next = { ...s };
        for (const item of res.items || []) next[item.medicine_id] = item.proposed_stock;
        return next;
      });
      setVoiceReview({ transcript: res.transcript || "", unmatched: res.unmatched || [] });
    } catch (e) {
      setVoiceError(e?.detail || e?.error || t("voice_failed"));
    } finally {
      setVoiceBusy(false);
    }
  }

  async function startVoice() {
    setVoiceError("");
    setVoiceReview(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = () => {
        stream.getTracks().forEach((tr) => tr.stop());
        sendVoice(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
      };
      mediaRef.current = { recorder, stream };
      recorder.start();
      setRecording(true);
    } catch {
      setVoiceError(t("voice_mic_denied"));
    }
  }

  function stopVoice() {
    const m = mediaRef.current;
    if (m?.recorder && m.recorder.state !== "inactive") m.recorder.stop();
    setRecording(false);
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
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{t("medicine_stock")}</h2>
                <p className="text-sm text-ink-muted">{t("how_much_left")}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {voiceSupported && (
                  <button
                    type="button"
                    onClick={recording ? stopVoice : startVoice}
                    disabled={voiceBusy}
                    className={`rounded-action border px-3 py-2 text-xs font-semibold disabled:opacity-60 ${
                      recording
                        ? "animate-pulse border-status-critical bg-status-critical-soft text-status-critical"
                        : "border-line-control text-ink hover:bg-line-light"
                    }`}
                  >
                    {voiceBusy
                      ? t("voice_reading")
                      : recording
                      ? `● ${t("voice_listening")}`
                      : `🎙 ${t("voice_report")}`}
                  </button>
                )}
                <label className="cursor-pointer rounded-action border border-line-control px-3 py-2 text-xs font-semibold text-ink hover:bg-line-light">
                  {extracting ? t("invoice_extracting") : t("scan_invoice")}
                  <input
                    type="file"
                    accept="image/*,application/pdf"
                    capture="environment"
                    disabled={extracting}
                    onChange={handleInvoiceFile}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
            {voiceReview && (
              <div className="mt-3 rounded-action bg-status-healthy-soft p-3 text-sm text-status-healthy-deep">
                <p className="font-medium">{t("voice_review")}</p>
                {voiceReview.transcript && (
                  <p className="mt-1 italic text-status-healthy-deep/80">
                    {t("voice_heard", { text: voiceReview.transcript })}
                  </p>
                )}
                {voiceReview.unmatched.length > 0 && (
                  <p className="mt-1 text-status-healthy-deep/80">
                    {t("voice_unmatched", { names: voiceReview.unmatched.join(", ") })}
                  </p>
                )}
              </div>
            )}
            {voiceError && (
              <p className="mt-3 rounded-action bg-status-critical-soft p-3 text-sm font-medium text-status-critical">
                {voiceError}
              </p>
            )}
            {invoiceReview && (
              <div className="mt-3 rounded-action bg-status-healthy-soft p-3 text-sm text-status-healthy-deep">
                <p className="font-medium">{t("invoice_extracted_review")}</p>
                {invoiceReview.unmatched.length > 0 && (
                  <p className="mt-1 text-status-healthy-deep/80">
                    {t("invoice_unmatched", { names: invoiceReview.unmatched.join(", ") })}
                  </p>
                )}
              </div>
            )}
            {invoiceError && (
              <p className="mt-3 rounded-action bg-status-critical-soft p-3 text-sm font-medium text-status-critical">
                {invoiceError}
              </p>
            )}
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
