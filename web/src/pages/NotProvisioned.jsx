import { useLang } from "../i18n/translations";

export default function NotProvisioned({ email, onSignOut }) {
  const { t } = useLang();
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-6">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-sm">
        <h1 className="text-xl font-semibold">{t("not_provisioned")}</h1>
        <p className="mt-3 text-sm text-ink/60">{email}</p>
        <button
          onClick={onSignOut}
          className="mt-6 rounded-xl border border-ink/20 px-6 py-3 font-medium"
        >
          {t("sign_out")}
        </button>
      </div>
    </div>
  );
}
