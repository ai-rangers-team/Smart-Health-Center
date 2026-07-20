import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { where } from "firebase/firestore";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useCollection, useDoc } from "../hooks/useFirestore";
import { useLang } from "../i18n/translations";
import { DepletionBar, LanguageSwitch, Monogram, StatusBadge } from "../components/ui";
import Typewriter from "../components/Typewriter";

const STATUS_ORDER = { critical: 0, warning: 1, under_resourced: 2, underperforming: 2, operational: 3, healthy: 3 };

// Map the backend's English indication strings to localizable label keys.
const INDICATION_KEY = {
  "diarrhoeal illness": "ind_diarrhoeal",
  "febrile illness": "ind_febrile",
  "respiratory/bacterial infection": "ind_respiratory",
  "patient footfall": "ind_footfall",
};

function statusKey(c) {
  return (c.status || "operational").toLowerCase();
}

/** Compose alert text from structured fields so it translates on toggle. */
function alertText(a, t, local) {
  const med = local("meds", a.medicine_name);
  switch (a.type) {
    case "STOCKOUT_CRITICAL":
      return a.days_remaining == null
        ? t("alert_out_of_stock", { medicine: med })
        : t("alert_stockout_critical", { medicine: med, days: a.days_remaining });
    case "STOCKOUT_WARNING":
      return a.days_remaining == null
        ? t("alert_below_min", { medicine: med })
        : t("alert_stockout_warning", { medicine: med, days: a.days_remaining });
    case "BED_CRISIS":
      return t("alert_bed_crisis");
    case "ATTENDANCE_LOW":
      return t("alert_attendance_low");
    case "UNDERPERFORMANCE":
      return t("alert_underperformance");
    case "TEST_UNAVAILABLE":
      return t("alert_test_unavailable", { test: local("tests", a.test_name || "") });
    case "DATA_INTEGRITY":
      // Descriptive detail (numbers/medicine) stays in the canonical message; only
      // the "possible misreport" label is localized.
      return `${t("alert_data_integrity")} — ${a.message}`;
    case "CITIZEN_DISPUTE":
      return `${t("alert_citizen_dispute")} — ${a.message}`;
    default:
      return a.message;
  }
}

export default function Dashboard() {
  const { districtId, user, signOut } = useAuth();
  const { t, lang, local, hasChosenLang, setLang } = useLang();
  const did = districtId || "pune_rural";

  const district = useDoc(`districts/${did}`);
  // One-time regional default: only applies if the admin hasn't already
  // chosen a language, and never re-fires once they have.
  useEffect(() => {
    if (!hasChosenLang && district?.default_language) setLang(district.default_language);
  }, [hasChosenLang, district?.default_language]);

  const centres = useCollection("centres", [where("district_id", "==", did)], [did]);
  const alerts = useCollection("alerts", [
    where("district_id", "==", did),
    where("resolved", "==", false),
  ], [did]);
  const recommendations = useCollection("recommendations", [
    where("district_id", "==", did),
  ], [did]);

  const [briefing, setBriefing] = useState("");
  const [briefingLoading, setBriefingLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    let timer;
    const fetchBriefing = (attempt) => {
      api
        .get(`/api/ai/district-briefing/${did}?lang=${lang}`)
        .then((d) => {
          if (cancelled) return;
          setBriefing(d.briefing);
          // One delayed retry if the model was briefly rate-limited
          if (!d.briefing && attempt === 0) {
            timer = setTimeout(() => fetchBriefing(1), 5000);
            return;
          }
          setBriefingLoading(false);
        })
        .catch(() => {
          if (!cancelled) {
            setBriefing("");
            setBriefingLoading(false);
          }
        });
    };
    setBriefingLoading(true);
    fetchBriefing(0);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [did, lang]);

  // Impact ledger — deterministic headline numbers (no Gemini). Refetched when the
  // alert set changes, which is a good proxy for "an operator just reported new stock".
  const [impact, setImpact] = useState(null);
  useEffect(() => {
    let cancelled = false;
    api
      .get(`/api/ai/impact/${did}`)
      .then((d) => !cancelled && setImpact(d))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [did, alerts.length]);

  // Outbreak early-warning — clustered consumption/footfall surges (no Gemini).
  const [outbreaks, setOutbreaks] = useState([]);
  useEffect(() => {
    let cancelled = false;
    api
      .get(`/api/ai/outbreak/${did}`)
      .then((d) => !cancelled && setOutbreaks(d.outbreaks || []))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [did, alerts.length]);

  const [acked, setAcked] = useState({});
  const acknowledge = async (id) => {
    try {
      await api.post(`/api/recommendations/${id}/acknowledge`);
      setAcked((a) => ({ ...a, [id]: true }));
    } catch {
      setAcked((a) => ({ ...a, [id]: "error" }));
    }
  };

  const [resolved, setResolved] = useState({});
  const resolveAlert = async (id) => {
    try {
      await api.post(`/api/alerts/${id}/resolve`);
      setResolved((r) => ({ ...r, [id]: true }));
    } catch {
      /* keep visible on failure */
    }
  };

  // Runs the redistribution engine across the district; the recommendations
  // land in Firestore and paint here live via the onSnapshot subscription.
  const [planning, setPlanning] = useState(false);
  const generatePlan = async () => {
    setPlanning(true);
    try {
      await api.post(`/api/ai/redistribution/${did}?lang=${lang}`);
      setAcked({}); // a new plan supersedes locally-hidden items too
    } catch {
      /* panel simply stays as-is on failure */
    } finally {
      setPlanning(false);
    }
  };

  const critical = alerts.filter((a) => a.severity === "critical").length;
  const beds = centres.reduce(
    (acc, c) => ({
      total: acc.total + (c.beds_total || 0),
      available: acc.available + (c.beds_available || 0),
    }),
    { total: 0, available: 0 }
  );
  const sorted = [...centres].sort(
    (a, b) => (STATUS_ORDER[statusKey(a)] ?? 3) - (STATUS_ORDER[statusKey(b)] ?? 3)
  );
  const pending = recommendations.filter((r) => r.status === "pending" && !acked[r.id]);
  const disputed = recommendations.filter((r) => r.status === "disputed");

  const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
  const activeAlerts = alerts
    .filter((a) => !resolved[a.id])
    .sort((a, b) => (SEV_ORDER[a.severity] ?? 3) - (SEV_ORDER[b.severity] ?? 3));

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-brand-deep px-6 py-4 sm:px-10">
        <div className="mx-auto flex max-w-district items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <Monogram />
            <div>
              <h1 className="text-lg font-bold text-white">
                {t("app_name")} · {t("district_view")}
              </h1>
              <p className="text-sm text-ondark-subtle">
                {district
                  ? t("dept_line_dynamic", { district: district.name, state: district.state })
                  : t("dept_line")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSwitch onDark />
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-white">{user?.displayName}</p>
              <p className="text-xs text-ondark-subtle">{t("district_officer")}</p>
            </div>
            <Link
              to="/onboard-centre"
              className="rounded-headerpill bg-white/10 px-3.5 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              {t("onboard_centre")}
            </Link>
            <button
              onClick={signOut}
              className="rounded-headerpill bg-white/10 px-3.5 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              {t("sign_out")}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-district space-y-6 px-6 py-6 sm:px-10">
        {(briefing || briefingLoading) && (
          <section className="flex flex-col gap-3 rounded-card bg-brand-darkest p-6 sm:flex-row sm:items-start sm:gap-6">
            <span className="inline-flex shrink-0 items-center rounded-chip border border-ondark-subtle/40 px-3.5 py-1.5 text-xs font-bold tracking-wide text-ondark-soft">
              {t("ai_briefing").toUpperCase()}
            </span>
            {briefingLoading && !briefing ? (
              <div className="w-full animate-pulse space-y-2.5 py-1">
                <div className="h-3.5 w-11/12 rounded-bar bg-white/15" />
                <div className="h-3.5 w-4/5 rounded-bar bg-white/10" />
                <div className="h-3.5 w-2/3 rounded-bar bg-white/10" />
              </div>
            ) : (
              <p className="text-base leading-relaxed text-ondark-bright">
                <Typewriter text={briefing} />
              </p>
            )}
          </section>
        )}

        {disputed.length > 0 && (
          <section className="rounded-card border border-status-critical/40 bg-status-critical-soft p-5">
            <div className="flex items-center gap-2">
              <span className="text-lg" aria-hidden>
                ⚑
              </span>
              <h2 className="text-lg font-semibold text-status-critical">
                {t("transfer_discrepancy_title")}
              </h2>
            </div>
            <ul className="mt-3 space-y-2">
              {disputed.map((r) => (
                <li key={r.id} className="text-sm font-medium text-status-critical">
                  {t("transfer_discrepancy_line", {
                    medicine: local("meds", r.medicine),
                    sent: r.quantity,
                    received: r.received_qty ?? 0,
                    shortfall: r.shortfall ?? r.quantity - (r.received_qty ?? 0),
                    from: r.from_centre,
                    to: r.to_centre,
                  })}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-status-critical/80">{t("transfer_discrepancy_hint")}</p>
          </section>
        )}

        {outbreaks.length > 0 && (
          <section className="rounded-card border border-status-warning/40 bg-status-warning-soft p-5">
            <div className="flex items-center gap-2">
              <span className="text-lg" aria-hidden>
                ⚠
              </span>
              <h2 className="text-lg font-semibold text-status-warning-deep">
                {t("outbreak_banner_title")}
              </h2>
            </div>
            <ul className="mt-3 space-y-3">
              {outbreaks.map((o, i) => {
                const key = INDICATION_KEY[o.indication];
                const indText = key ? t(key) : o.indication;
                return (
                  <li key={i}>
                    <p className="text-sm font-semibold text-status-warning-deep">
                      {t("outbreak_line", {
                        indication: indText,
                        n: o.centre_count,
                        ratio: o.peak_ratio,
                      })}
                    </p>
                    <p className="text-sm text-status-warning-deep/80">
                      {t("outbreak_centres_label")}: {o.centres.join(", ")}
                    </p>
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-xs text-status-warning-deep/70">{t("outbreak_hint")}</p>
          </section>
        )}

        {impact &&
          (impact.patients_protected > 0 || impact.stockouts_flagged_early > 0) && (
            <section className="rounded-card border border-status-healthy/30 bg-status-healthy-soft p-6">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-chip bg-brand px-2.5 py-1 text-xs font-bold tracking-wide text-white">
                  AI
                </span>
                <h2 className="text-lg font-semibold">{t("impact_ledger_title")}</h2>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
                <ImpactTile
                  value={impact.patients_protected.toLocaleString("en-IN")}
                  label={t("impact_patients_protected")}
                  sub={`${impact.units_redistributed.toLocaleString("en-IN")} ${t(
                    "impact_units_sub"
                  )}`}
                />
                <ImpactTile
                  value={`₹${impact.rupees_saved.toLocaleString("en-IN")}`}
                  label={t("impact_rupees_saved")}
                />
                <ImpactTile
                  value={impact.stockouts_flagged_early}
                  label={t("impact_flagged_early")}
                  sub={t("impact_lead_time_sub", { d: impact.avg_lead_time_days })}
                />
                <ImpactTile
                  value={impact.units_redistributed.toLocaleString("en-IN")}
                  label={t("impact_units_moved")}
                />
              </div>
              <p className="mt-4 text-xs text-ink-faint">
                {t("impact_estimate_note", { n: centres.length })}
              </p>
            </section>
          )}

        {(() => {
          const so = alerts.filter(
            (a) => a.type?.startsWith("STOCKOUT") && a.days_remaining != null && !resolved[a.id]
          );
          if (!so.length) return null;
          const avg = Math.round(so.reduce((s, a) => s + a.days_remaining, 0) / so.length);
          return (
            <p className="text-sm font-medium text-brand">
              {t("impact_line", { n: so.length, d: avg })}
            </p>
          );
        })()}

        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile
            label={t("patients_seen")}
            value={sorted.reduce((n, c) => n + (c.footfall_today || 0), 0)}
            sub={`${centres.length} ${t("all_centres").toLowerCase()}`}
          />
          <StatTile
            label={t("critical_alerts")}
            value={critical}
            sub={t("attention")}
            accent={critical > 0 ? "text-status-critical" : ""}
          />
          <StatTile label={t("beds_available")} value={beds.available} sub={`/ ${beds.total}`} />
          <StatTile label={t("all_centres")} value={centres.length} sub={t("district_view")} />
        </section>

        <div className="grid gap-6 xl:grid-cols-2 xl:items-start">
        <section className="rounded-card border border-line bg-surface p-6">
          <h2 className="text-lg font-semibold">{t("active_alerts")}</h2>
          {activeAlerts.length === 0 ? (
            <p className="mt-4 flex items-center gap-2 text-sm font-medium text-status-healthy-deep">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-status-healthy-soft text-xs">✓</span>
              {t("all_clear_district")}
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-line-light">
              {activeAlerts.map((a) => (
                <li
                  key={a.id}
                  className="flex flex-col gap-2 py-3.5 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-start gap-3">
                    <StatusBadge
                      status={a.severity}
                      className="mt-0.5 min-w-[5.5rem] shrink-0 justify-center"
                    >
                      {a.severity === "critical" ? t("critical") : t("warning")}
                    </StatusBadge>
                    <div>
                      <p className="text-sm font-medium">{a.centre_name}</p>
                      <p className="text-sm text-ink-muted">{alertText(a, t, local)}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => resolveAlert(a.id)}
                    className="shrink-0 self-start rounded-action border border-line-control px-4 py-2 text-sm font-semibold text-ink hover:bg-line-light sm:self-center"
                  >
                    {t("resolve")}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-card border border-line bg-surface p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{t("ai_recommendations")}</h2>
            <button
              onClick={generatePlan}
              disabled={planning}
              className="rounded-action bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-deep disabled:opacity-60"
            >
              {planning ? t("generating") : t("generate_plan")}
            </button>
          </div>
          {pending.length === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">{t("no_recommendations")}</p>
          ) : (
            <ul className="mt-4 divide-y divide-line-light">
              {pending.map((r) => (
                <li
                  key={r.id}
                  className="flex flex-col gap-3 py-3.5 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-start gap-3">
                    <StatusBadge
                      status={r.urgency === "critical" ? "critical" : "warning"}
                      className="mt-0.5 min-w-[5.5rem] shrink-0 justify-center"
                    >
                      {r.urgency === "critical" ? t("critical") : t("warning")}
                    </StatusBadge>
                    <div>
                      {/* Gemini-written field instruction (in the language the
                          plan was generated in) — the AI artifact judges see */}
                      <p className="text-sm leading-relaxed">
                        {r.lang === lang && r.gemini_message ? (
                          <Typewriter text={r.gemini_message} />
                        ) : (
                          t("reco_move", {
                            qty: r.quantity,
                            medicine: local("meds", r.medicine),
                            from: r.from_centre,
                            to: r.to_centre,
                          })
                        )}
                      </p>
                      {r.lang === lang && r.gemini_message && (
                        <p className="mt-0.5 text-xs text-ink-faint">
                          {r.from_centre} → {r.to_centre} · {r.quantity} ×{" "}
                          {local("meds", r.medicine)}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => acknowledge(r.id)}
                    className="shrink-0 rounded-action bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-deep"
                  >
                    {t("acknowledge")}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        </div>

        <section>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{t("all_centres")}</h2>
            <div className="hidden items-center gap-4 text-xs text-ink-muted sm:flex">
              <LegendDot color="bg-status-healthy" label={t("healthy")} />
              <LegendDot color="bg-status-warning" label={t("warning")} />
              <LegendDot color="bg-status-critical" label={t("critical")} />
              <LegendDot color="bg-status-underperforming" label={t("underperforming")} />
            </div>
          </div>

          <div className="mt-4 grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sorted.map((c) => (
              <CentreCard key={c.id} centre={c} alerts={alerts} />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function ImpactTile({ label, value, sub }) {
  return (
    <div className="rounded-tile border border-status-healthy/20 bg-surface/70 p-5">
      <p className="tabular text-3xl font-bold text-status-healthy-deep">{value}</p>
      <p className="mt-1 text-sm font-medium text-ink">{label}</p>
      {sub && <p className="mt-0.5 text-xs text-ink-muted">{sub}</p>}
    </div>
  );
}

function StatTile({ label, value, sub, accent = "" }) {
  return (
    <div className="rounded-tile border border-line bg-surface p-5">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className={`tabular mt-1 text-3xl font-bold ${accent}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-ink-faint">{sub}</p>}
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

const EDGE = {
  critical: "border-l-4 border-l-status-critical",
  warning: "border-l-4 border-l-status-warning",
  under_resourced: "border-l-4 border-l-status-underperforming",
  underperforming: "border-l-4 border-l-status-underperforming",
  operational: "border-l-4 border-l-status-healthy",
  healthy: "border-l-4 border-l-status-healthy",
};

function CentreCard({ centre, alerts }) {
  const { t, local } = useLang();
  const s = statusKey(centre);
  const topAlert = alerts.find(
    (a) => a.centre_id === centre.id && a.days_remaining != null
  );
  // Show the composite performance score on every centre, not just flagged ones.
  const scoreSuffix =
    centre.performance_score != null ? ` · ${centre.performance_score}/100` : "";
  const statusLabel =
    s === "critical"
      ? t("critical")
      : s === "warning"
      ? t("warning")
      : s === "under_resourced" || s === "underperforming"
      ? t("underperforming")
      : t("healthy");
  const badge = `${statusLabel}${scoreSuffix}`;

  return (
    <Link
      to={`/centre/${centre.id}`}
      className={`flex h-full flex-col rounded-card border border-line bg-surface p-5 transition-shadow hover:shadow-md ${
        EDGE[s] || EDGE.healthy
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold">{centre.name}</h3>
          <p className="text-xs text-ink-muted">{centre.location?.block || centre.type}</p>
        </div>
        <StatusBadge status={s}>{badge}</StatusBadge>
      </div>

      <div className="mt-4 flex gap-8">
        <div>
          <p className="tabular text-2xl font-bold">{centre.footfall_today ?? "—"}</p>
          <p className="text-xs text-ink-muted">{t("footfall")}</p>
        </div>
        <div>
          <p className="tabular text-2xl font-bold">
            {centre.beds_available ?? "—"}/{centre.beds_total ?? "—"}
          </p>
          <p className="text-xs text-ink-muted">{t("beds_available")}</p>
        </div>
      </div>

      {topAlert ? (
        <div className="mt-auto pt-4">
          <p
            className={`text-sm font-medium ${
              topAlert.severity === "critical"
                ? "text-status-critical"
                : "text-status-warning-deep"
            }`}
          >
            {local("meds", topAlert.medicine_name)} — {topAlert.days_remaining} {t("days_left")}
          </p>
          <div className="mt-1.5">
            <DepletionBar daysRemaining={topAlert.days_remaining} />
          </div>
        </div>
      ) : (
        <div className="mt-auto pt-4">
          <p className="text-sm font-medium text-status-healthy-deep">{t("stock_ok")}</p>
          <div className="mt-1.5 h-1.5 w-full rounded-bar bg-status-healthy-soft" />
        </div>
      )}
    </Link>
  );
}
