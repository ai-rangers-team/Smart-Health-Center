import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useLang } from "../i18n/translations";
import { Choice2, LanguageSwitch, Stepper } from "../components/ui";

const inputClass =
  "mt-3 w-full rounded-stepper-sm border border-line-control bg-canvas px-3.5 py-2.5 text-ink focus:border-brand focus:outline-none";

/**
 * district_admin onboards a new centre's identity + who runs it — nothing
 * operational. Stock/tests/beds all start at neutral defaults and are
 * established by the operator's first real daily report (MyCentre.jsx).
 */
export default function OnboardCentre() {
  const { signOut } = useAuth();
  const { t } = useLang();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [isPHC, setIsPHC] = useState(true);
  const [block, setBlock] = useState("");
  const [operatorEmail, setOperatorEmail] = useState("");
  const [expectedPatients, setExpectedPatients] = useState(60);
  const [saving, setSaving] = useState(false);
  const [bulk, setBulk] = useState(null); // {done, total, created, failed: [{line, error}]}
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null); // {centre_id, operator}

  async function createCentre() {
    setSaving(true);
    setError("");
    try {
      const res = await api.post("/api/centres", {
        name,
        type: isPHC ? "PHC" : "CHC",
        block,
        operator_email: operatorEmail || null,
        expected_daily_patients: expectedPatients || null,
      });
      setCreated(res);
    } catch (e) {
      setError(
        e?.detail || e?.error || "Could not create the centre. Check the details and try again."
      );
    } finally {
      setSaving(false);
    }
  }

  function downloadTemplate() {
    const csv =
      "name,type,block,operator_email,expected_daily_patients\n" +
      "PHC Wagholi,PHC,Wagholi Taluka,operator@example.com,60\n" +
      "PHC Shirur,PHC,Shirur Taluka,,80\n";
    const a = document.createElement("a");
    a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
    a.download = "centres_template.csv";
    a.click();
  }

  async function handleBulkFile(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    const text = await file.text();
    const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    if (!lines.length) return;
    // Skip a header row if present
    const rows = /^name\s*,/i.test(lines[0]) ? lines.slice(1) : lines;
    const failed = [];
    let createdCount = 0;
    setBulk({ done: 0, total: rows.length, created: 0, failed: [] });
    for (let i = 0; i < rows.length; i++) {
      const [rname, rtype, rblock, remail, rpatients] = rows[i]
        .split(",")
        .map((c) => (c || "").trim());
      try {
        if (!rname || !rblock) throw { error: "name and block are required" };
        await api.post("/api/centres", {
          name: rname,
          type: (rtype || "PHC").toUpperCase() === "CHC" ? "CHC" : "PHC",
          block: rblock,
          operator_email: remail || null,
          expected_daily_patients: parseInt(rpatients, 10) || null,
        });
        createdCount++;
      } catch (err) {
        failed.push({ line: rname || `line ${i + 1}`, error: err?.detail || err?.error || "failed" });
      }
      setBulk({ done: i + 1, total: rows.length, created: createdCount, failed });
    }
  }

  if (created) {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-phone flex-col bg-canvas md:max-w-4xl">
        <header className="bg-brand-deep px-5 pb-4 pt-3 text-white md:rounded-b-card">
          <div className="flex items-center justify-between">
            <LanguageSwitch onDark />
            <button
              onClick={signOut}
              className="rounded-headerpill bg-white/10 px-3 py-1.5 text-sm font-medium"
            >
              {t("sign_out")}
            </button>
          </div>
        </header>
        <main className="flex-1 px-4 pt-4">
          <section className="rounded-card border border-status-healthy/30 bg-status-healthy-soft p-5">
            <p className="font-semibold text-status-healthy-deep">
              ✓ {t("centre_created_title")}
            </p>
            <p className="mt-1 text-sm text-status-healthy-deep/80">{created.centre_id}</p>
            {created.operator && (
              <p className="mt-2 text-sm text-status-healthy-deep/80">
                {created.operator.provisioned
                  ? t("operator_provisioned_yes")
                  : t("operator_provisioned_pending")}
              </p>
            )}
          </section>
          <button
            onClick={() => navigate("/")}
            className="mt-4 w-full rounded-card bg-brand py-4 text-lg font-semibold text-white hover:bg-brand-deep"
          >
            {t("back")}
          </button>
        </main>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-phone flex-col bg-canvas md:max-w-4xl">
      <header className="bg-brand-deep px-5 pb-4 pt-3 text-white md:rounded-b-card">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-sm font-medium text-ondark-soft hover:text-white">
            &lsaquo; {t("all_centres")}
          </Link>
          <div className="flex items-center gap-3">
            <LanguageSwitch onDark />
            <button
              onClick={signOut}
              className="rounded-headerpill bg-white/10 px-3 py-1.5 text-sm font-medium"
            >
              {t("sign_out")}
            </button>
          </div>
        </div>
        <h1 className="mt-2 text-xl font-bold">{t("onboard_centre")}</h1>
      </header>

      <main className="flex-1 px-4 pb-32 pt-4">
        {error && (
          <section className="mb-4 rounded-card bg-status-critical-soft p-4 text-sm font-medium text-status-critical">
            {error}
          </section>
        )}

        <div className="space-y-4">
          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("centre_name_label")}</h2>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="PHC Wagholi"
              className={inputClass}
            />
          </section>

          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("centre_type_label")}</h2>
            <div className="mt-3">
              <Choice2 value={isPHC} onChange={setIsPHC} onLabel="PHC" offLabel="CHC" />
            </div>
          </section>

          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("block_label")}</h2>
            <input
              value={block}
              onChange={(e) => setBlock(e.target.value)}
              placeholder="Wagholi Taluka"
              className={inputClass}
            />
          </section>

          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("expected_patients_label")}</h2>
            <p className="mt-1 text-xs text-ink-muted">{t("expected_patients_hint")}</p>
            <div className="mt-4 flex justify-center">
              <Stepper value={expectedPatients} onChange={setExpectedPatients} min={1} />
            </div>
          </section>

          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("operator_email_label")}</h2>
            <input
              value={operatorEmail}
              onChange={(e) => setOperatorEmail(e.target.value)}
              type="email"
              placeholder="operator@example.com"
              className={inputClass}
            />
            <p className="mt-2 text-xs text-ink-muted">{t("operator_email_hint")}</p>
          </section>

          <section className="rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold">{t("bulk_title")}</h2>
            <p className="mt-1 text-xs text-ink-muted">{t("bulk_hint")}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={downloadTemplate}
                className="rounded-action border border-line-control px-4 py-2.5 text-sm font-semibold text-ink hover:bg-line-light"
              >
                {t("bulk_template")}
              </button>
              <label className="cursor-pointer rounded-action bg-brand px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-deep">
                {t("bulk_upload")}
                <input type="file" accept=".csv,text/csv" onChange={handleBulkFile} className="hidden" />
              </label>
            </div>
            {bulk && (
              <div className="mt-4 space-y-2 text-sm">
                {bulk.done < bulk.total ? (
                  <p className="font-medium">
                    {t("bulk_progress", { done: bulk.done + 1, total: bulk.total })}
                  </p>
                ) : (
                  <p className="font-medium text-status-healthy-deep">
                    {t("bulk_done", { n: bulk.created })}
                  </p>
                )}
                {bulk.failed.length > 0 && bulk.done >= bulk.total && (
                  <div className="rounded-action bg-status-critical-soft p-3 text-status-critical">
                    <p className="font-semibold">{t("bulk_failed", { n: bulk.failed.length })}</p>
                    <ul className="mt-1 list-inside list-disc">
                      {bulk.failed.map((f, i) => (
                        <li key={i}>
                          {f.line} — {f.error}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </main>

      <div className="fixed inset-x-0 bottom-0 mx-auto w-full max-w-phone bg-gradient-to-t from-canvas via-canvas to-transparent p-4 md:max-w-4xl">
        <button
          onClick={createCentre}
          disabled={saving || !name.trim() || !block.trim()}
          className="w-full rounded-card bg-brand py-4 text-lg font-semibold text-white hover:bg-brand-deep disabled:opacity-60"
        >
          {saving ? "…" : t("create_centre_button")}
        </button>
      </div>
    </div>
  );
}
