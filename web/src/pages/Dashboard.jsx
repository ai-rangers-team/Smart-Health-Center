import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { where } from "firebase/firestore";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useCollection } from "../hooks/useFirestore";
import { useLang } from "../i18n/translations";
import { DepletionBar, LanguageSwitch, Monogram, StatusBadge } from "../components/ui";

const STATUS_ORDER = { critical: 0, warning: 1, under_resourced: 2, underperforming: 2, operational: 3, healthy: 3 };

function statusKey(c) {
  return (c.status || "operational").toLowerCase();
}

/** Compose alert text from structured fields so it translates on toggle. */
function alertText(a, t, local) {
  const med = local("meds", a.medicine_name);
  switch (a.type) {
    case "STOCKOUT_CRITICAL":
      return t("alert_stockout_critical", { medicine: med, days: a.days_remaining });
    case "STOCKOUT_WARNING":
      return t("alert_stockout_warning", { medicine: med, days: a.days_remaining });
    case "BED_CRISIS":
      return t("alert_bed_crisis");
    case "ATTENDANCE_LOW":
      return t("alert_attendance_low");
    case "UNDERPERFORMANCE":
      return t("alert_underperformance");
    case "TEST_UNAVAILABLE":
      return t("alert_test_unavailable", { test: local("tests", a.test_name || "") });
    default:
      return a.message;
  }
}

export default function Dashboard() {
  const { districtId, user, signOut } = useAuth();
  const { t, lang, local } = useLang();
  const did = districtId || "pune_rural";

  const centres = useCollection("centres", [where("district_id", "==", did)]);
  const alerts = useCollection("alerts", [
    where("district_id", "==", did),
    where("resolved", "==", false),
  ]);
  const recommendations = useCollection("recommendations", [
    where("district_id", "==", did),
  ]);

  const [briefing, setBriefing] = useState("");
  useEffect(() => {
    api
      .get(`/api/ai/district-briefing/${did}?lang=${lang}`)
      .then((d) => setBriefing(d.briefing))
      .catch(() => setBriefing(""));
  }, [did, lang]);

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
              <p className="text-sm text-ondark-subtle">{t("dept_line")}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSwitch onDark />
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-white">{user?.displayName}</p>
              <p className="text-xs text-ondark-subtle">{t("district_officer")}</p>
            </div>
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
        {briefing && (
          <section className="flex flex-col gap-3 rounded-card bg-brand-darkest p-6 sm:flex-row sm:items-start sm:gap-6">
            <span className="inline-flex shrink-0 items-center rounded-chip border border-ondark-subtle/40 px-3.5 py-1.5 text-xs font-bold tracking-wide text-ondark-soft">
              {t("ai_briefing").toUpperCase()}
            </span>
            <p className="text-base leading-relaxed text-ondark-bright">{briefing}</p>
          </section>
        )}

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
        {activeAlerts.length > 0 && (
          <section className="rounded-card border border-line bg-surface p-6">
            <h2 className="text-lg font-semibold">{t("active_alerts")}</h2>
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
          </section>
        )}

        {pending.length > 0 && (
          <section className="rounded-card border border-line bg-surface p-6">
            <h2 className="text-lg font-semibold">{t("ai_recommendations")}</h2>
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
                    <p className="text-sm leading-relaxed">
                      {t("reco_move", {
                        qty: r.quantity,
                        medicine: local("meds", r.medicine),
                        from: r.from_centre,
                        to: r.to_centre,
                      })}
                    </p>
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
          </section>
        )}
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

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sorted.map((c) => (
              <CentreCard key={c.id} centre={c} alerts={alerts} />
            ))}
          </div>
        </section>
      </main>
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
  const badge =
    s === "critical"
      ? t("critical")
      : s === "warning"
      ? t("warning")
      : s === "under_resourced" || s === "underperforming"
      ? `${t("underperforming")} · ${centre.performance_score ?? "—"}/100`
      : t("healthy");

  return (
    <Link
      to={`/centre/${centre.id}`}
      className={`block rounded-card border border-line bg-surface p-5 transition-shadow hover:shadow-md ${
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
            {centre.beds_occupied ?? "—"}/{centre.beds_total ?? "—"}
          </p>
          <p className="text-xs text-ink-muted">{t("beds_available")}</p>
        </div>
      </div>

      {topAlert && (
        <div className="mt-4">
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
      )}
    </Link>
  );
}
