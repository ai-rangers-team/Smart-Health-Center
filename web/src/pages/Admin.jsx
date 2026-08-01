import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useLang } from "../i18n/translations";
import { LanguageSwitch, StatusBadge, Stepper } from "../components/ui";

const inputClass =
  "w-full rounded-stepper-sm border border-line-control bg-canvas px-3.5 py-2.5 text-sm text-ink focus:border-brand focus:outline-none";

/**
 * Super-admin console — the management plane of the whole platform.
 * Overview (what needs attention), people & access (grant / change / revoke),
 * districts, per-centre medicine catalogs, system health (technical
 * observability), and the append-only activity log.
 */
const SECTIONS = ["overview", "people", "districts", "medicines", "system", "activity"];

export default function Admin() {
  const { user, signOut } = useAuth();
  const { t } = useLang();
  // Section lives in the URL (?section=…) so console views are bookmarkable.
  const [params, setParams] = useSearchParams();
  const raw = params.get("section");
  const section = SECTIONS.includes(raw) ? raw : "overview";
  const setSection = (s) => setParams(s === "overview" ? {} : { section: s });
  const [sys, setSys] = useState(undefined);       // /api/admin/system
  const [overview, setOverview] = useState(undefined);
  const [centres, setCentres] = useState([]);

  async function refresh() {
    const [s, o, c] = await Promise.all([
      api.get("/api/admin/system").catch(() => null),
      api.get("/api/admin/overview").catch(() => null),
      api.get("/api/admin/centres-list").catch(() => ({ centres: [] })),
    ]);
    setSys(s?.alerts ? s : null);
    setOverview(o?.districts ? o : null);
    setCentres(c?.centres || []);
  }
  useEffect(() => { refresh(); }, []);

  const NAV = [
    ["overview", t("admin_nav_overview")],
    ["people", t("admin_tab_users")],
    ["districts", t("admin_tab_districts")],
    ["medicines", t("admin_tab_medicines")],
    ["system", t("admin_nav_system")],
    ["activity", t("admin_tab_activity")],
  ];

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="bg-brand-deep text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-5 py-4">
          <div>
            <h1 className="text-lg font-semibold">{t("admin_title")}</h1>
            <p className="text-xs text-white/70">{user?.email}</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={refresh}
              className="rounded-headerpill bg-white/10 px-3.5 py-2 text-sm font-medium hover:bg-white/20">
              {t("admin_refresh")}
            </button>
            <LanguageSwitch onDark />
            <button onClick={signOut}
              className="rounded-action border border-white/30 px-3 py-1.5 text-sm hover:bg-white/10">
              {t("sign_out")}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6 md:flex-row">
        <nav className="flex shrink-0 gap-2 overflow-x-auto md:w-52 md:flex-col md:overflow-visible">
          {NAV.map(([k, label]) => (
            <button key={k} onClick={() => setSection(k)}
              className={`whitespace-nowrap rounded-action px-4 py-2.5 text-left text-sm font-semibold ${
                section === k ? "bg-brand text-white" : "border border-line-control bg-white hover:bg-line-light"}`}>
              {label}
            </button>
          ))}
        </nav>

        <main className="min-w-0 flex-1">
          {section === "overview" && <Overview sys={sys} overview={overview} go={setSection} />}
          {section === "people" && <PeopleSection centres={centres} districts={overview?.districts || []} onChanged={refresh} />}
          {section === "districts" && <DistrictsSection overview={overview} onChanged={refresh} />}
          {section === "medicines" && <MedicinesSection centres={centres} />}
          {section === "system" && <SystemSection sys={sys} />}
          {section === "activity" && <ActivitySection centres={centres} />}
        </main>
      </div>
    </div>
  );
}

function Card({ title, hint, children, className = "" }) {
  return (
    <section className={`mb-5 rounded-card border border-line bg-white p-5 ${className}`}>
      {title && <h2 className="font-semibold">{title}</h2>}
      {hint && <p className="mt-1 text-sm text-ink-muted">{hint}</p>}
      <div className={title ? "mt-4" : ""}>{children}</div>
    </section>
  );
}

function Stat({ n, label, tone = "" }) {
  return (
    <div className="rounded-card border border-line bg-white p-4">
      <div className={`text-2xl font-bold ${tone}`}>{n}</div>
      <div className="mt-1 text-xs text-ink-muted">{label}</div>
    </div>
  );
}

/* ================= overview ================= */

function Overview({ sys, overview, go }) {
  const { t } = useLang();
  if (sys === undefined || overview === undefined)
    return <p className="text-ink-muted">{t("generating")}</p>;
  if (!sys || !overview) return <p className="text-critical">{t("admin_failed")}</p>;

  const att = sys.attention;
  const attentionCount = att.silent_centres.length + att.weak_centres.length
    + sys.alerts.disputes + sys.alerts.integrity;

  return (
    <>
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat n={overview.districts.length} label={t("admin_stat_districts")} />
        <Stat n={overview.total_centres} label={t("admin_stat_centres")} />
        <Stat n={overview.total_users} label={t("admin_stat_users")} />
        <Stat n={sys.alerts.total} label={t("admin_stat_alerts")}
          tone={sys.alerts.by_severity.critical ? "text-critical" : ""} />
        <Stat n={sys.feedback_today} label={t("admin_stat_feedback_today")} />
      </div>

      <Card title={t("admin_needs_attention")}>
        {attentionCount === 0 && att.users_never_signed_in.length === 0 ? (
          <p className="text-sm text-brand">{t("admin_all_clear")}</p>
        ) : (
          <div className="space-y-3 text-sm">
            {att.silent_centres.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-2 rounded-stepper-sm bg-critical-soft px-3 py-2.5">
                <span>
                  <b>{c.name}</b>{" — "}
                  {c.days_silent == null
                    ? t("admin_silent_never")
                    : t("admin_silent_line", { days: c.days_silent })}
                </span>
                <span className="text-xs text-ink-muted">{c.district_id}</span>
              </div>
            ))}
            {att.weak_centres.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-2 rounded-stepper-sm bg-warning-soft px-3 py-2.5">
                <span><b>{c.name}</b> — {t("admin_weak_line", { score: c.score ?? "—" })}</span>
                <span className="text-xs text-ink-muted">{c.district_id}</span>
              </div>
            ))}
            {(sys.alerts.disputes > 0 || sys.alerts.integrity > 0) && (
              <div className="rounded-stepper-sm bg-warning-soft px-3 py-2.5">
                {t("admin_open_flags_line", { disputes: sys.alerts.disputes, flags: sys.alerts.integrity })}
              </div>
            )}
            {att.users_never_signed_in.length > 0 && (
              <button onClick={() => go("people")}
                className="block w-full rounded-stepper-sm bg-line-light px-3 py-2.5 text-left">
                {t("admin_pending_users_line")}{" "}
                <span className="text-ink-muted">{att.users_never_signed_in.join(", ")}</span>
              </button>
            )}
          </div>
        )}
      </Card>

      <Card title={t("admin_tab_districts")}>
        <div className="divide-y divide-line-light">
          {overview.districts.map((d) => (
            <div key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <div className="font-semibold">{d.name}</div>
                <div className="text-sm text-ink-muted">
                  {d.state} · {t("admin_centres_count", { n: d.centres })} · {(d.default_language || "en").toUpperCase()}
                </div>
              </div>
              <Link to={`/reports?district=${d.id}`}
                className="rounded-action border border-line-control px-3 py-1.5 text-sm hover:bg-line-light">
                {t("reports_title")}
              </Link>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

/* ================= people & access ================= */

const ROLE_TONE = {
  super_admin: "bg-brand-deep text-white",
  district_admin: "bg-brand text-white",
  phc_operator: "bg-line-light text-ink",
};

function PeopleSection({ centres, districts, onChanged }) {
  const { t } = useLang();
  const [users, setUsers] = useState(null);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null); // email being edited
  const [msg, setMsg] = useState(null);

  const roleLabel = {
    district_admin: t("district_officer"),
    phc_operator: t("health_worker"),
    super_admin: t("admin_role_super"),
  };

  const refresh = () =>
    api.get("/api/admin/users").then((d) => setUsers(d.users || [])).catch(() => setUsers([]));
  useEffect(() => { refresh(); }, []);

  const shown = useMemo(
    () => (users || []).filter((u) => u.email.includes(query.toLowerCase())),
    [users, query]);

  async function save(payload) {
    setMsg(null);
    try {
      const res = await api.post("/api/admin/users", payload);
      setMsg({ ok: true, text: res.applies_now ? t("admin_user_saved") : t("admin_user_saved_pending") });
      setEditing(null);
      refresh(); onChanged();
      return true;
    } catch (e) {
      setMsg({ ok: false, text: e?.detail || e?.error || t("admin_failed") });
      return false;
    }
  }

  async function remove(email) {
    if (!window.confirm(t("admin_user_remove_confirm", { email }))) return;
    try { await api.delete(`/api/admin/users/${encodeURIComponent(email)}`); refresh(); onChanged(); }
    catch (e) { setMsg({ ok: false, text: e?.detail || t("admin_failed") }); }
  }

  return (
    <>
      <Card title={t("admin_add_user")} hint={t("admin_add_user_hint")}>
        <UserForm centres={centres} districts={districts} onSave={save} />
        {msg && <p className={`mt-3 text-sm ${msg.ok ? "text-brand" : "text-critical"}`}>{msg.text}</p>}
      </Card>

      <Card title={t("admin_tab_users")}>
        <input className={inputClass + " mb-3 max-w-sm"} placeholder={t("admin_search_users")}
          value={query} onChange={(e) => setQuery(e.target.value)} />
        {users === null ? <p className="text-ink-muted">{t("generating")}</p> : (
          <div className="divide-y divide-line-light">
            {shown.map((u) => (
              <div key={u.email} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-semibold">{u.email}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                      <span className={`rounded-full px-2.5 py-0.5 font-semibold ${ROLE_TONE[u.role] || "bg-line-light"}`}>
                        {roleLabel[u.role] || u.role}
                      </span>
                      {u.district_id && <span className="rounded-full bg-line-light px-2.5 py-0.5">{u.district_id}</span>}
                      {u.centre_id && <span className="rounded-full bg-line-light px-2.5 py-0.5">{u.centre_id}</span>}
                      {u.signed_in === false && (
                        <span className="rounded-full bg-warning-soft px-2.5 py-0.5">{t("admin_never_signed_in")}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => setEditing(editing === u.email ? null : u.email)}
                      className="rounded-action border border-line-control px-3 py-1.5 text-sm hover:bg-line-light">
                      {t("admin_change_role")}
                    </button>
                    <button onClick={() => remove(u.email)}
                      className="rounded-action border border-line-control px-3 py-1.5 text-sm text-critical hover:bg-critical-soft">
                      {t("admin_remove")}
                    </button>
                  </div>
                </div>
                {editing === u.email && (
                  <div className="mt-3 rounded-stepper-sm bg-canvas p-3">
                    <UserForm centres={centres} districts={districts} fixedEmail={u.email}
                      initialRole={u.role} initialCentre={u.centre_id} initialDistrict={u.district_id}
                      onSave={save} onCancel={() => setEditing(null)} />
                  </div>
                )}
              </div>
            ))}
            {shown.length === 0 && <p className="py-2 text-sm text-ink-muted">—</p>}
          </div>
        )}
      </Card>
    </>
  );
}

function UserForm({ centres, districts, onSave, onCancel, fixedEmail,
  initialRole = "phc_operator", initialCentre = "", initialDistrict = "" }) {
  const { t } = useLang();
  const [email, setEmail] = useState(fixedEmail || "");
  const [role, setRole] = useState(initialRole);
  const [centreId, setCentreId] = useState(initialCentre || "");
  const [districtId, setDistrictId] = useState(initialDistrict || "");
  const [busy, setBusy] = useState(false);

  const incomplete = !email
    || (role === "phc_operator" && !centreId)
    || (role === "district_admin" && !districtId);

  async function submit() {
    setBusy(true);
    const ok = await onSave({
      email: email.trim(),
      role,
      centre_id: role === "phc_operator" ? centreId : null,
      district_id: role === "district_admin" ? districtId : null,
    });
    setBusy(false);
    if (ok && !fixedEmail) { setEmail(""); setCentreId(""); setDistrictId(""); }
  }

  return (
    <div className="grid gap-3 md:grid-cols-4">
      {!fixedEmail && (
        <input className={inputClass} placeholder="name@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} />
      )}
      <select className={inputClass} value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="phc_operator">{t("health_worker")}</option>
        <option value="district_admin">{t("district_officer")}</option>
        <option value="super_admin">{t("admin_role_super")}</option>
      </select>
      {role === "phc_operator" && (
        <select className={inputClass} value={centreId} onChange={(e) => setCentreId(e.target.value)}>
          <option value="">{t("admin_their_centre")}</option>
          {centres.map((c) => <option key={c.id} value={c.id}>{c.name} · {c.district_id}</option>)}
        </select>
      )}
      {role === "district_admin" && (
        <select className={inputClass} value={districtId} onChange={(e) => setDistrictId(e.target.value)}>
          <option value="">{t("admin_their_district")}</option>
          {districts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      )}
      <div className="flex gap-2">
        <button onClick={submit} disabled={busy || incomplete}
          className="rounded-action bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {t("admin_save_user")}
        </button>
        {onCancel && (
          <button onClick={onCancel}
            className="rounded-action border border-line-control px-4 py-2 text-sm">
            {t("admin_cancel")}
          </button>
        )}
      </div>
    </div>
  );
}

/* ================= districts ================= */

function DistrictsSection({ overview, onChanged }) {
  const { t } = useLang();
  const [form, setForm] = useState({ name: "", state: "" });
  const [msg, setMsg] = useState(null);

  async function create() {
    setMsg(null);
    try {
      await api.post("/api/admin/districts", form);
      setForm({ name: "", state: "" });
      setMsg({ ok: true, text: t("admin_district_created") });
      onChanged();
    } catch (e) { setMsg({ ok: false, text: e?.detail || t("admin_failed") }); }
  }

  return (
    <>
      <Card title={t("admin_add_district")} hint={t("admin_add_district_hint")}>
        <div className="grid gap-3 md:grid-cols-3">
          <input className={inputClass} placeholder={t("admin_district_name")} value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={inputClass} placeholder={t("admin_state_name")} value={form.state}
            onChange={(e) => setForm({ ...form, state: e.target.value })} />
          <button onClick={create} disabled={!form.name || !form.state}
            className="rounded-action bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {t("admin_create_district")}
          </button>
        </div>
        {msg && <p className={`mt-3 text-sm ${msg.ok ? "text-brand" : "text-critical"}`}>{msg.text}</p>}
      </Card>

      <Card title={t("admin_tab_districts")}>
        {!overview ? <p className="text-ink-muted">{t("generating")}</p> : (
          <div className="divide-y divide-line-light">
            {overview.districts.map((d) => (
              <div key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <div className="font-semibold">{d.name}</div>
                  <div className="text-sm text-ink-muted">
                    {d.state} · {t("admin_centres_count", { n: d.centres })} · {(d.default_language || "en").toUpperCase()}
                  </div>
                </div>
                <Link to={`/reports?district=${d.id}`}
                  className="rounded-action border border-line-control px-3 py-1.5 text-sm hover:bg-line-light">
                  {t("reports_title")}
                </Link>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}

/* ================= medicine catalog ================= */

function MedicinesSection({ centres }) {
  const { t, local } = useLang();
  const [centreId, setCentreId] = useState("");
  const [meds, setMeds] = useState(null);
  const [form, setForm] = useState({ name: "", unit: "tablets" });
  const [msg, setMsg] = useState(null);

  const loadMeds = (id) =>
    api.get(`/api/admin/centres/${id}/medicines`).then((d) => setMeds(d.medicines || [])).catch(() => setMeds([]));
  useEffect(() => { if (centreId) { setMeds(null); loadMeds(centreId); } }, [centreId]);

  async function addMed() {
    setMsg(null);
    try {
      await api.post(`/api/admin/centres/${centreId}/medicines`, form);
      setForm({ name: "", unit: form.unit });
      loadMeds(centreId);
    } catch (e) { setMsg({ ok: false, text: e?.detail || t("admin_failed") }); }
  }

  async function setThreshold(medId, field, value) {
    try {
      await api.patch(`/api/admin/centres/${centreId}/medicines/${medId}`, { [field]: value });
      loadMeds(centreId);
    } catch { /* keep UI state */ }
  }

  async function removeMed(m) {
    if (!window.confirm(t("admin_medicine_remove_confirm", { name: m.medicine_name }))) return;
    await api.delete(`/api/admin/centres/${centreId}/medicines/${m.id}`).catch(() => {});
    loadMeds(centreId);
  }

  return (
    <Card title={t("admin_tab_medicines")} hint={t("admin_medicines_hint")}>
      <select className={inputClass + " max-w-md"} value={centreId}
        onChange={(e) => setCentreId(e.target.value)}>
        <option value="">{t("admin_pick_centre")}</option>
        {centres.map((c) => <option key={c.id} value={c.id}>{c.name} · {c.district_id}</option>)}
      </select>

      {centreId && meds === null && <p className="mt-4 text-ink-muted">{t("generating")}</p>}
      {centreId && meds && (
        <>
          <div className="mt-4 divide-y divide-line-light">
            {meds.map((m) => (
              <div key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-40">
                  <div className="font-semibold">{local("meds", m.medicine_name) || m.medicine_name}</div>
                  <div className="text-sm text-ink-muted">
                    {local("units", m.unit)} · {t("admin_current_stock", { n: m.current_stock ?? 0 })}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-5">
                  <label className="text-sm text-ink-muted">
                    {t("admin_min_level")}
                    <div className="mt-1"><Stepper value={m.min_threshold || 0}
                      onChange={(v) => setThreshold(m.id, "min_threshold", v)} /></div>
                  </label>
                  <label className="text-sm text-ink-muted">
                    {t("admin_reorder_level")}
                    <div className="mt-1"><Stepper value={m.reorder_level || 0}
                      onChange={(v) => setThreshold(m.id, "reorder_level", v)} /></div>
                  </label>
                  <button onClick={() => removeMed(m)}
                    className="rounded-action border border-line-control px-3 py-1.5 text-sm text-critical hover:bg-critical-soft">
                    {t("admin_remove")}
                  </button>
                </div>
              </div>
            ))}
            {meds.length === 0 && <p className="py-2 text-sm text-ink-muted">—</p>}
          </div>

          <div className="mt-5 grid gap-3 border-t border-line pt-4 md:grid-cols-3">
            <input className={inputClass} placeholder={t("admin_medicine_name")} value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <select className={inputClass} value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}>
              {["tablets", "sachets", "vials"].map((u) => (
                <option key={u} value={u}>{local("units", u)}</option>
              ))}
            </select>
            <button onClick={addMed} disabled={!form.name}
              className="rounded-action bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
              {t("admin_add_medicine")}
            </button>
          </div>
          <p className="mt-2 text-xs text-ink-muted">{t("admin_add_medicine_hint")}</p>
          {msg && <p className="mt-2 text-sm text-critical">{msg.text}</p>}
        </>
      )}
    </Card>
  );
}

/* ================= system health / observability ================= */

function SystemSection({ sys }) {
  const { t } = useLang();
  if (sys === undefined) return <p className="text-ink-muted">{t("generating")}</p>;
  if (!sys) return <p className="text-critical">{t("admin_failed")}</p>;

  const perf = [...(sys.centres || [])].sort((a, b) => (a.score ?? 101) - (b.score ?? 101));

  return (
    <>
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat n={t("admin_sys_online")} label={t("admin_sys_api")} tone="text-brand" />
        <Stat n={`${sys.firestore.read_ms} ms`} label={t("admin_sys_db")} />
        <Stat n={sys.gemini.model} label={t("admin_sys_ai")} />
        <Stat n={sys.gemini.auth === "api_key" ? t("admin_sys_auth_key") : t("admin_sys_auth_vertex")}
          label={t("admin_sys_ai_auth")} />
      </div>

      <Card title={t("admin_sys_briefings")} hint={t("admin_sys_briefings_hint")}>
        <div className="space-y-2 text-sm">
          {Object.entries(sys.briefing_cache).map(([district, langs]) => (
            <div key={district} className="flex flex-wrap items-center gap-2">
              <span className="w-40 font-semibold">{district}</span>
              {["en", "hi", "mr", "te"].map((l) => (
                <span key={l}
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    langs.includes(l) ? "bg-brand text-white" : "bg-line-light text-ink-muted"}`}>
                  {l.toUpperCase()}
                </span>
              ))}
            </div>
          ))}
        </div>
      </Card>

      <Card title={t("admin_sys_performance")} hint={t("admin_sys_perf_hint")}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-ink-muted">
                {[t("reports_col_centre"), t("admin_col_district"), t("admin_col_status"),
                  t("admin_col_score"), t("admin_col_today"), ""].map((h, i) => (
                  <th key={i} className="px-3 py-2.5 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {perf.map((c) => (
                <tr key={c.id} className="border-b border-line-light last:border-0">
                  <td className="px-3 py-2.5 font-semibold">{c.name}</td>
                  <td className="px-3 py-2.5 text-ink-muted">{c.district_id}</td>
                  <td className="px-3 py-2.5">
                    {c.status && (
                      <StatusBadge status={c.status}>
                        {t(c.status === "under_resourced" ? "underperforming"
                          : c.status === "operational" ? "healthy" : c.status)}
                      </StatusBadge>
                    )}
                  </td>
                  <td className={`px-3 py-2.5 font-semibold ${(c.score ?? 100) < 60 ? "text-critical" : ""}`}>
                    {c.score ?? "—"}/100
                  </td>
                  <td className="px-3 py-2.5">{c.footfall_today ?? "—"}</td>
                  <td className="px-3 py-2.5">
                    <a href={`/p/${c.id}`} target="_blank" rel="noreferrer"
                      className="text-xs text-brand underline">{t("admin_view_public")}</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

/* ================= activity log ================= */

function ActivitySection({ centres }) {
  const { t } = useLang();
  const [entries, setEntries] = useState(null);
  const [centreId, setCentreId] = useState("");

  useEffect(() => {
    setEntries(null);
    const q = centreId ? `&centre_id=${centreId}` : "";
    api.get(`/api/admin/audit?limit=80${q}`)
      .then((d) => setEntries(d.entries || [])).catch(() => setEntries([]));
  }, [centreId]);

  const actionLabel = (a) => {
    const key = `act_${a}`;
    const label = t(key);
    return label === key ? a : label; // graceful fallback for unknown actions
  };

  const fmtVal = (v) => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${k}: ${x}`).join(", ");
    return String(v);
  };

  return (
    <Card title={t("admin_tab_activity")} hint={t("admin_activity_hint")}>
      <select className={inputClass + " mb-3 max-w-sm"} value={centreId}
        onChange={(e) => setCentreId(e.target.value)}>
        <option value="">{t("admin_all_centres_filter")}</option>
        {centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      {entries === null ? <p className="text-ink-muted">{t("generating")}</p> : (
        <div className="divide-y divide-line-light text-sm">
          {entries.map((e) => (
            <div key={e.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5">
              <div className="min-w-0">
                <span className="font-semibold">{actionLabel(e.action)}</span>
                <span className="text-ink-muted"> · {e.centre_id !== "-" ? e.centre_id : ""}</span>
                {(e.before !== undefined || e.after !== undefined) && (
                  <span className="block truncate text-xs text-ink-muted">
                    {fmtVal(e.before)} → {fmtVal(e.after)}
                  </span>
                )}
                <span className="block text-xs text-ink-muted">
                  {e.actor?.email || e.actor?.uid || "—"}
                  {e.actor?.channel && e.actor.channel !== "app" ? ` · ${e.actor.channel}` : ""}
                </span>
              </div>
              <span className="text-xs text-ink-muted">{String(e.at).slice(0, 19).replace("T", " ")}</span>
            </div>
          ))}
          {entries.length === 0 && <p className="py-2 text-ink-muted">—</p>}
        </div>
      )}
    </Card>
  );
}
