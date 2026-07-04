import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useLang } from "../i18n/translations";
import { Choice2, LanguageSwitch } from "../components/ui";

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
  const [saving, setSaving] = useState(false);
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
          <LanguageSwitch onDark />
          <button
            onClick={signOut}
            className="rounded-headerpill bg-white/10 px-3 py-1.5 text-sm font-medium"
          >
            {t("sign_out")}
          </button>
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
