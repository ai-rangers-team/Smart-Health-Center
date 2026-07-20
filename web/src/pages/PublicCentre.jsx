import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useLang } from "../i18n/translations";
import { LanguageSwitch, Monogram } from "../components/ui";

const STATUS_STYLE = {
  available: "bg-status-healthy-soft text-status-healthy-deep",
  low: "bg-status-warning-soft text-status-warning-deep",
  out: "bg-status-critical-soft text-status-critical",
};
const STATUS_KEY = { available: "med_available", low: "med_low", out: "med_out" };

/**
 * Public, no-login citizen status page (QR poster target: /p/:centreId).
 * Reads only the coarse availability fields the public endpoint exposes.
 */
export default function PublicCentre() {
  const { centreId } = useParams();
  const { t, local } = useLang();
  const [c, setC] = useState(undefined); // undefined = loading, null = not found
  const [fb, setFb] = useState({ doctor: null, medicine: null });
  const [fbDone, setFbDone] = useState(false);

  async function submitFeedback() {
    if (fb.doctor === null || fb.medicine === null) return;
    try {
      await api.post(`/api/public/centre/${centreId}/feedback`, {
        doctor_present: fb.doctor,
        medicine_available: fb.medicine,
      });
    } catch {
      /* best-effort — still thank the citizen */
    }
    setFbDone(true);
  }

  useEffect(() => {
    let cancelled = false;
    api
      .get(`/api/public/centre/${centreId}`)
      .then((d) => !cancelled && setC(d))
      .catch(() => !cancelled && setC(null));
    return () => {
      cancelled = true;
    };
  }, [centreId]);

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
        {c === undefined ? (
          <div className="animate-pulse space-y-3">
            <div className="h-7 w-2/3 rounded-bar bg-line-track" />
            <div className="h-4 w-1/2 rounded-bar bg-line-track" />
            <div className="mt-4 h-20 rounded-tile bg-line-track" />
            <div className="h-40 rounded-tile bg-line-track" />
          </div>
        ) : c === null ? (
          <p className="mt-16 text-center text-ink-muted">{t("public_not_found")}</p>
        ) : (
          <>
            <span className="inline-flex items-center rounded-chip bg-status-healthy-soft px-3 py-1 text-xs font-semibold text-status-healthy-deep">
              {t("public_for_citizens")}
            </span>
            <h1 className="mt-3 text-2xl font-bold">{c.name}</h1>
            <p className="text-sm text-ink-muted">
              {c.block ? `${c.block} · ` : ""}
              {t("public_status")}
            </p>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div
                className={`rounded-tile p-4 ${
                  c.doctor_present ? "bg-status-healthy-soft" : "bg-status-critical-soft"
                }`}
              >
                <p
                  className={`text-sm font-semibold ${
                    c.doctor_present ? "text-status-healthy-deep" : "text-status-critical"
                  }`}
                >
                  {c.doctor_present ? t("public_doctor_present") : t("public_doctor_absent")}
                </p>
              </div>
              <div className="rounded-tile border border-line bg-surface p-4">
                <p className="tabular text-2xl font-bold">
                  {c.beds?.available ?? "—"}/{c.beds?.total ?? "—"}
                </p>
                <p className="text-xs text-ink-muted">{t("public_beds_free")}</p>
              </div>
            </div>

            <section className="mt-6">
              <h2 className="font-semibold">{t("public_medicines")}</h2>
              <ul className="mt-3 space-y-2">
                {(c.medicines || []).map((m) => (
                  <li
                    key={m.id}
                    className="flex items-center justify-between rounded-tile border border-line bg-surface px-4 py-3"
                  >
                    <span className="text-sm font-medium">{local("meds", m.name)}</span>
                    <span
                      className={`rounded-chip px-3 py-1 text-xs font-semibold ${
                        STATUS_STYLE[m.status] || STATUS_STYLE.available
                      }`}
                    >
                      {t(STATUS_KEY[m.status] || "med_available")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="mt-6">
              <h2 className="font-semibold">{t("public_tests")}</h2>
              <ul className="mt-3 space-y-2">
                {Object.entries(c.tests || {}).map(([name, avail]) => (
                  <li
                    key={name}
                    className="flex items-center justify-between rounded-tile border border-line bg-surface px-4 py-3"
                  >
                    <span className="text-sm font-medium capitalize">{local("tests", name)}</span>
                    <span
                      className={`rounded-chip px-3 py-1 text-xs font-semibold ${
                        avail ? STATUS_STYLE.available : STATUS_STYLE.out
                      }`}
                    >
                      {avail ? t("available") : t("not_available")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="mt-8 rounded-card border border-line bg-surface p-5">
              {fbDone ? (
                <p className="py-2 text-center text-sm font-medium text-status-healthy-deep">
                  ✓ {t("feedback_thanks")}
                </p>
              ) : (
                <>
                  <h2 className="font-semibold">{t("feedback_title")}</h2>
                  <div className="mt-4 space-y-4">
                    <YesNo
                      label={t("feedback_doctor_q")}
                      value={fb.doctor}
                      onChange={(v) => setFb((s) => ({ ...s, doctor: v }))}
                      t={t}
                    />
                    <YesNo
                      label={t("feedback_medicine_q")}
                      value={fb.medicine}
                      onChange={(v) => setFb((s) => ({ ...s, medicine: v }))}
                      t={t}
                    />
                  </div>
                  <button
                    onClick={submitFeedback}
                    disabled={fb.doctor === null || fb.medicine === null}
                    className="mt-5 w-full rounded-action bg-brand py-3 text-sm font-semibold text-white hover:bg-brand-deep disabled:opacity-50"
                  >
                    {t("feedback_submit")}
                  </button>
                </>
              )}
            </section>

            <p className="mt-6 text-center text-xs text-ink-faint">{t("public_updated")}</p>
          </>
        )}
      </main>
    </div>
  );
}

function YesNo({ label, value, onChange, t }) {
  const btn = (v, text) =>
    `flex-1 rounded-action border px-4 py-2 text-sm font-semibold ${
      value === v
        ? v
          ? "border-status-healthy bg-status-healthy-soft text-status-healthy-deep"
          : "border-status-critical bg-status-critical-soft text-status-critical"
        : "border-line-control text-ink hover:bg-line-light"
    }`;
  return (
    <div>
      <p className="text-sm font-medium">{label}</p>
      <div className="mt-2 flex gap-3">
        <button className={btn(true)} onClick={() => onChange(true)}>
          {t("feedback_yes")}
        </button>
        <button className={btn(false)} onClick={() => onChange(false)}>
          {t("feedback_no")}
        </button>
      </div>
    </div>
  );
}
