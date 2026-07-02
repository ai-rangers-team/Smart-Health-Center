import { useLang } from "../i18n/translations";

/** Placeholder — replaced by the approved Claude Design port. */
export default function Login({ onSignIn }) {
  const { t } = useLang();
  return (
    <div className="flex min-h-screen items-center justify-center bg-teal-deep p-6">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold">{t("app_name")}</h1>
        <p className="mt-1 text-sm text-ink/60">{t("dept_line")}</p>
        <button
          onClick={onSignIn}
          className="mt-8 w-full rounded-xl bg-teal px-6 py-4 text-lg font-semibold text-white"
        >
          {t("sign_in_google")}
        </button>
      </div>
    </div>
  );
}
