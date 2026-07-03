import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { limit, orderBy } from "firebase/firestore";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useCollection, useDoc } from "../hooks/useFirestore";
import { useLang } from "../i18n/translations";
import { DepletionBar, LanguageSwitch, StatusBadge } from "../components/ui";

const ESSENTIAL_TESTS = ["malaria", "tb", "pregnancy", "diabetes", "hiv"];

export default function CentreDetail() {
  const { centreId } = useParams();
  const { signOut } = useAuth();
  const { t, lang, local } = useLang();

  const centre = useDoc(`centres/${centreId}`);
  const stock = useCollection(`centres/${centreId}/stock`);
  const beds = useDoc(`centres/${centreId}/beds/current`);
  const tests = useDoc(`centres/${centreId}/tests/current`);
  const attendance = useCollection(`centres/${centreId}/attendance`, [
    orderBy("date", "desc"),
    limit(7),
  ]);
  const footfall = useCollection(`centres/${centreId}/footfall`, [
    orderBy("date", "desc"),
    limit(30),
  ]);

  const [explanation, setExplanation] = useState("");
  const flagged =
    centre && ["under_resourced", "underperforming", "critical"].includes(centre.status);
  useEffect(() => {
    if (!flagged) return;
    api
      .post(`/api/ai/explain-underperformance/${centreId}?lang=${lang}`)
      .then((d) => setExplanation(d.explanation))
      .catch(() => setExplanation(""));
  }, [centreId, flagged, lang]);

  if (!centre) return <div className="p-10 text-ink-muted">Loading…</div>;

  const attData = [...attendance].reverse().map((a) => ({
    day: a.date?.slice(6),
    rate: Math.round((a.attendance_rate || 0) * 100),
  }));
  const footData = [...footfall].reverse().map((f) => ({
    day: f.date?.slice(6),
    count: f.count || 0,
  }));
  const isUnder = ["under_resourced", "underperforming"].includes(centre.status);

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-brand-deep px-6 py-4 sm:px-10">
        <div className="mx-auto flex max-w-detail items-center justify-between">
          <Link to="/" className="text-sm font-medium text-ondark-soft hover:text-white">
            &lsaquo; {t("all_centres")}
          </Link>
          <div className="flex items-center gap-4">
            <LanguageSwitch onDark />
            <button
              onClick={signOut}
              className="rounded-headerpill bg-white/10 px-3.5 py-2 text-sm font-medium text-white hover:bg-white/20"
            >
              {t("sign_out")}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-detail space-y-6 px-6 py-6 sm:px-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">{centre.name}</h1>
            <p className="text-sm text-ink-muted">
              {centre.location?.block || centre.type}
            </p>
          </div>
          <StatusBadge status={centre.status || "healthy"}>
            {isUnder
              ? `${t("underperforming")} · ${centre.performance_score ?? "—"}/100`
              : t(centre.status === "critical" ? "critical" : "healthy")}
          </StatusBadge>
        </div>

        {flagged && explanation && (
          <section className="rounded-card bg-status-underperforming-soft p-5">
            <h2 className="flex items-center gap-2 text-base font-semibold text-status-underperforming-deep">
              <span className="rounded-headerpill bg-white px-2 py-0.5 text-xs font-bold">
                AI
              </span>
              {t("why_flagged")}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-status-underperforming-deep">
              {explanation}
            </p>
          </section>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-card border border-line bg-surface p-6">
            <div className="flex justify-between">
              <div>
                <p className="text-sm text-ink-muted">{t("patients_seen_today")}</p>
                <p className="tabular text-4xl font-bold">{footfall[0]?.count ?? "—"}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-ink-muted">{t("staff_present")}</p>
                <p className="tabular text-4xl font-bold">
                  {attendance[0]
                    ? `${
                        attendance[0].doctors_present + (attendance[0].nurses_present || 0)
                      }/${attendance[0].doctors_total + (attendance[0].nurses_total || 0)}`
                    : "—"}
                </p>
              </div>
            </div>

            {beds && (
              <div className="mt-6">
                <div className="flex justify-between text-sm">
                  <span className="text-ink-muted">{t("bed_occupancy")}</span>
                  <span className="font-medium">
                    {beds.occupied} {t("of")} {beds.total}
                  </span>
                </div>
                <div className="mt-2 h-2 rounded-bar bg-line-track">
                  <div
                    className="h-2 rounded-bar bg-status-info"
                    style={{
                      width: `${Math.min(100, (beds.occupied / (beds.total || 1)) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            )}

            <div className="mt-6">
              <p className="text-xs font-semibold tracking-wide text-ink-faint">
                {t("patients_last_7").toUpperCase()}
              </p>
              <div className="mt-2 h-36">
                <ResponsiveContainer>
                  <BarChart data={attData}>
                    <XAxis dataKey="day" tickLine={false} axisLine={false} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="rate" fill="#0E6E58" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-1 text-center text-xs text-ink-faint">{t("attendance")} %</p>
            </div>
          </section>

          <section className="rounded-card border border-line bg-surface p-6">
            <h2 className="text-base font-semibold">{t("medicine_stock")}</h2>
            <ul className="mt-4 space-y-4">
              {stock.map((m) => (
                <li key={m.id}>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">
                      {m.medicine_name}
                      {local("meds", m.medicine_name) !== m.medicine_name && (
                        <span className="ml-2 text-xs text-ink-muted">
                          {local("meds", m.medicine_name)}
                        </span>
                      )}
                    </p>
                    <span
                      className={`rounded-chip px-2.5 py-0.5 text-xs font-semibold ${
                        m.days_remaining <= 3
                          ? "bg-status-critical-soft text-status-critical"
                          : m.days_remaining <= 7
                          ? "bg-status-warning-soft text-status-warning-deep"
                          : "bg-status-healthy-soft text-status-healthy-deep"
                      }`}
                    >
                      {m.days_remaining != null ? `${m.days_remaining} ${t("days_left")}` : "—"}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3">
                    <div className="flex-1">
                      <DepletionBar daysRemaining={m.days_remaining ?? 21} />
                    </div>
                    <span className="tabular text-xs text-ink-faint">
                      {m.current_stock} {local("units", m.unit)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className="rounded-card border border-line bg-surface p-6">
          <p className="text-xs font-semibold tracking-wide text-ink-faint">
            {t("footfall_last_30").toUpperCase()}
          </p>
          <div className="mt-3 h-44">
            <ResponsiveContainer>
              <LineChart data={footData}>
                <CartesianGrid stroke="#F0EEE7" vertical={false} />
                <XAxis dataKey="day" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis width={30} tickLine={false} axisLine={false} fontSize={11} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#0E6E58"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {tests && (
          <section className="rounded-card border border-line bg-surface p-6">
            <h2 className="text-base font-semibold">{t("tests_section")}</h2>
            <div className="mt-4 flex flex-wrap gap-3">
              {ESSENTIAL_TESTS.map((name) => {
                const ok = tests[name] !== false;
                return (
                  <span
                    key={name}
                    className={`inline-flex items-center gap-1.5 rounded-chip px-3.5 py-1.5 text-sm font-medium capitalize ${
                      ok
                        ? "bg-status-healthy-soft text-status-healthy-deep"
                        : "bg-status-critical-soft text-status-critical"
                    }`}
                  >
                    {ok ? "✓" : "✕"} {local("tests", name)}
                  </span>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
