import { useLang } from "../i18n/translations";
import { LanguageSwitch, Monogram } from "../components/ui";

/**
 * Entry screen — ported from the approved design (deep brand ground, SHC
 * monogram, bilingual dept line). Real auth is Google Sign-In; the role is
 * read from custom claims and routing happens automatically in App.jsx.
 */
export default function Login({ onSignIn }) {
  const { t } = useLang();
  return (
    <div className="flex min-h-screen flex-col bg-brand-deep">
      <header className="flex items-center justify-between px-6 py-5 sm:px-10">
        <div className="flex items-center gap-3.5">
          <Monogram />
          <div>
            <h1 className="text-xl font-bold text-white">{t("app_name")}</h1>
            <p className="text-sm text-ondark-subtle">{t("dept_line")}</p>
          </div>
        </div>
        <LanguageSwitch onDark />
      </header>

      <main className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md rounded-role bg-surface p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-card bg-status-healthy-soft">
            <svg
              viewBox="0 0 24 24"
              className="h-6 w-6 text-brand"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M12 21C7 17 3 13.5 3 9.5A5.5 5.5 0 0 1 12 5a5.5 5.5 0 0 1 9 4.5c0 4-4 7.5-9 11.5Z" />
              <path d="M12 9v4M10 11h4" strokeLinecap="round" />
            </svg>
          </div>
          <h2 className="mt-5 text-2xl font-bold">{t("app_name")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t("dept_line")}</p>

          <button
            onClick={onSignIn}
            className="mt-8 flex w-full items-center justify-center gap-3 rounded-card bg-brand px-6 py-4 text-base font-semibold text-white hover:bg-brand-deep"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
              <path
                fill="currentColor"
                d="M21.35 11.1H12v2.9h5.35c-.5 2.5-2.6 3.9-5.35 3.9a5.9 5.9 0 1 1 0-11.8c1.5 0 2.85.55 3.9 1.45l2.15-2.15A8.9 8.9 0 1 0 12 20.9c4.45 0 8.55-3.25 8.55-8.9 0-.3-.05-.6-.1-.9Z"
              />
            </svg>
            {t("sign_in_google")}
          </button>

          <p className="mt-6 text-xs text-ink-faint">Supported by Google Cloud</p>
        </div>
      </main>
    </div>
  );
}
