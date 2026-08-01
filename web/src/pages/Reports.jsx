import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useLang } from "../i18n/translations";
import { LanguageSwitch, StatusBadge } from "../components/ui";

/**
 * District period report for the DHO and roles above — the page a health
 * officer prints (browser print -> PDF, A4-friendly) or exports as CSV and
 * forwards upward. Read-only aggregation of what the system already records.
 * A super admin opens it per-district via ?district=<id> from the console.
 */
export default function Reports() {
  const { user, districtId: ownDistrict, signOut } = useAuth();
  const { t } = useLang();
  const [params] = useSearchParams();
  const [days, setDays] = useState(30);
  const [report, setReport] = useState(undefined); // undefined = loading
  const districtId = params.get("district") || ownDistrict;

  useEffect(() => {
    if (!districtId) return;
    let cancelled = false;
    setReport(undefined);
    api
      .get(`/api/district/${districtId}/report?days=${days}`)
      .then((d) => !cancelled && setReport(d?.centres ? d : null))
      .catch(() => !cancelled && setReport(null));
    return () => { cancelled = true; };
  }, [districtId, days]);

  function exportCsv() {
    if (!report) return;
    const head = ["centre", "type", "status", "score", "patients",
      "avg_per_day", "days_reported", "compliance_pct", "avg_attendance_pct",
      "stock_out", "stock_low", "active_alerts"];
    const rows = report.centres.map((c) => [
      c.name, c.type, c.status ?? "", c.performance_score ?? "", c.patients,
      c.avg_patients_per_day, c.days_reported, c.compliance_pct,
      c.avg_attendance_pct ?? "", c.stock.out, c.stock.low,
      Object.values(c.alerts || {}).reduce((a, b) => a + b, 0),
    ]);
    const csv = [head, ...rows]
      .map((r) => r.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const a = document.createElement("a");
    a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
    a.download = `district-report-${report.period.from}-to-${report.period.to}.csv`;
    a.click();
  }

  const alertsTotal = report
    ? Object.values(report.alerts_by_type || {}).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="bg-brand-deep text-white print:hidden">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-5 py-4">
          <div>
            <Link to="/" className="text-sm text-white/70 hover:text-white">
              ← {t("back")}
            </Link>
            <h1 className="text-lg font-semibold">{t("reports_title")}</h1>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitch onDark />
            <button onClick={signOut}
              className="rounded-action border border-white/30 px-3 py-1.5 text-sm hover:bg-white/10">
              {t("sign_out")}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-6 print:max-w-none print:px-0">
        {/* Print-only letterhead */}
        <div className="hidden print:block print:mb-4">
          <h1 className="text-xl font-bold">{t("reports_title")}</h1>
        </div>

        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 print:hidden">
          <div className="flex gap-2">
            {[7, 30].map((d) => (
              <button key={d} onClick={() => setDays(d)}
                className={`rounded-action px-4 py-2 text-sm font-semibold ${
                  days === d ? "bg-brand text-white" : "border border-line-control bg-white"}`}>
                {d === 7 ? t("reports_weekly") : t("reports_monthly")}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={exportCsv} disabled={!report}
              className="rounded-action border border-line-control bg-white px-4 py-2 text-sm font-semibold">
              {t("reports_export_csv")}
            </button>
            <button onClick={() => window.print()} disabled={!report}
              className="rounded-action bg-brand px-4 py-2 text-sm font-semibold text-white">
              {t("reports_download_pdf")}
            </button>
          </div>
        </div>

        {report === undefined && <p className="text-ink-muted">{t("generating")}</p>}
        {report === null && <p className="text-critical">{t("reports_failed")}</p>}

        {report && (
          <>
            <p className="mb-4 text-sm text-ink-muted">
              {report.district_name} · {report.period.from} → {report.period.to}
            </p>

            <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                [report.totals.patients, t("reports_total_patients")],
                [report.totals.avg_attendance_pct != null
                  ? `${report.totals.avg_attendance_pct}%` : "—", t("reports_avg_attendance")],
                [`${report.totals.centres_fully_compliant}/${report.totals.centres}`,
                  t("reports_compliant_centres")],
                [alertsTotal, t("reports_active_alerts")],
              ].map(([n, l]) => (
                <div key={l} className="rounded-card border border-line bg-white p-4">
                  <div className="text-2xl font-bold">{n}</div>
                  <div className="mt-1 text-xs text-ink-muted">{l}</div>
                </div>
              ))}
            </div>

            <div className="overflow-x-auto rounded-card border border-line bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs text-ink-muted">
                    {[t("reports_col_centre"), t("reports_col_patients"),
                      t("reports_col_reported"), t("reports_col_attendance"),
                      t("reports_col_stock"), t("reports_col_alerts")].map((h) => (
                      <th key={h} className="px-4 py-3 font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.centres.map((c) => (
                    <tr key={c.id} className="border-b border-line-light last:border-0">
                      <td className="px-4 py-3">
                        <div className="font-semibold">{c.name}</div>
                        {c.status && (
                          <StatusBadge status={c.status} className="mt-1">
                            {t(c.status === "under_resourced" ? "underperforming"
                              : c.status === "operational" ? "healthy" : c.status)}
                          </StatusBadge>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {c.patients}
                        <span className="text-xs text-ink-muted"> · {c.avg_patients_per_day}/{t("reports_per_day")}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={c.compliance_pct < 70 ? "font-semibold text-critical" : ""}>
                          {c.days_reported}/{report.period.days} ({c.compliance_pct}%)
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {c.avg_attendance_pct != null ? `${c.avg_attendance_pct}%` : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {c.stock.out > 0 && (
                          <span className="mr-2 font-semibold text-critical">{c.stock.out} {t("reports_stock_out")}</span>
                        )}
                        {c.stock.low > 0 && (
                          <span className="text-warning-strong">{c.stock.low} {t("reports_stock_low")}</span>
                        )}
                        {c.stock.out === 0 && c.stock.low === 0 && (
                          <span className="text-brand">{t("stock_ok")}</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {Object.values(c.alerts || {}).reduce((a, b) => a + b, 0) || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 rounded-card border border-line bg-white p-4 text-sm">
              <h2 className="mb-2 font-semibold">{t("reports_accountability")}</h2>
              <p className="text-ink-muted">
                {t("reports_accountability_line", {
                  fb: report.citizen_feedback.reports_in_period,
                  disputes: report.citizen_feedback.disputes_active,
                  flags: report.citizen_feedback.integrity_flags_active,
                })}
              </p>
            </div>

            <p className="mt-4 text-xs text-ink-muted">
              {t("reports_generated_note")} · {user?.email}
            </p>
          </>
        )}
      </main>
    </div>
  );
}
