import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../hooks/useAuth";
import { useLang } from "../i18n/translations";
import { LanguageSwitch, Stepper } from "../components/ui";

const inputClass =
  "w-full rounded-stepper-sm border border-line-control bg-canvas px-3.5 py-2.5 text-ink focus:border-brand focus:outline-none";

/**
 * Super-admin console: users & roles, districts, per-centre medicine catalogs,
 * and the audit trail. Written in the same plain language as the rest of the
 * app — a state official should be able to run this without a manual.
 */
export default function Admin() {
  const { user, signOut } = useAuth();
  const { t } = useLang();
  const [tab, setTab] = useState("users");
  const tabs = [
    ["users", t("admin_tab_users")],
    ["districts", t("admin_tab_districts")],
    ["medicines", t("admin_tab_medicines")],
    ["activity", t("admin_tab_activity")],
  ];

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="bg-brand-deep text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-5 py-4">
          <div>
            <h1 className="text-lg font-semibold">{t("admin_title")}</h1>
            <p className="text-xs text-white/70">{user?.email}</p>
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

      <main className="mx-auto max-w-6xl px-5 py-6">
        <div className="mb-6 flex flex-wrap gap-2">
          {tabs.map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)}
              className={`rounded-action px-4 py-2 text-sm font-semibold ${
                tab === k ? "bg-brand text-white" : "border border-line-control bg-white"}`}>
              {label}
            </button>
          ))}
        </div>
        {tab === "users" && <UsersTab />}
        {tab === "districts" && <DistrictsTab />}
        {tab === "medicines" && <MedicinesTab />}
        {tab === "activity" && <ActivityTab />}
      </main>
    </div>
  );
}

function SectionCard({ title, hint, children }) {
  return (
    <section className="mb-5 rounded-card border border-line bg-white p-5">
      <h2 className="font-semibold">{title}</h2>
      {hint && <p className="mt-1 text-sm text-ink-muted">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

/* ---------------- users & roles ---------------- */

function UsersTab() {
  const { t } = useLang();
  const [users, setUsers] = useState(null);
  const [centres, setCentres] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [form, setForm] = useState({ email: "", role: "phc_operator", centre_id: "", district_id: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null); // {ok, text}

  async function refresh() {
    const [u, o, c] = await Promise.all([
      api.get("/api/admin/users"),
      api.get("/api/admin/overview"),
      api.get("/api/admin/centres-list").catch(() => ({ centres: [] })),
    ]);
    setUsers(u.users || []);
    setDistricts(o.districts || []);
    setCentres(c.centres || []);
  }
  useEffect(() => { refresh().catch(() => setUsers([])); }, []);

  async function save() {
    setBusy(true); setMsg(null);
    try {
      const res = await api.post("/api/admin/users", {
        email: form.email.trim(),
        role: form.role,
        centre_id: form.role === "phc_operator" ? form.centre_id || null : null,
        district_id: form.role === "district_admin" ? form.district_id || null : null,
      });
      setMsg({ ok: true, text: res.applies_now ? t("admin_user_saved") : t("admin_user_saved_pending") });
      setForm({ email: "", role: form.role, centre_id: "", district_id: "" });
      refresh();
    } catch (e) {
      setMsg({ ok: false, text: e?.detail || e?.error || t("admin_failed") });
    } finally { setBusy(false); }
  }

  async function remove(email) {
    if (!window.confirm(t("admin_user_remove_confirm", { email }))) return;
    try { await api.delete(`/api/admin/users/${encodeURIComponent(email)}`); refresh(); }
    catch (e) { setMsg({ ok: false, text: e?.detail || t("admin_failed") }); }
  }

  const roleLabel = { district_admin: t("district_officer"), phc_operator: t("health_worker"),
    super_admin: t("admin_role_super") };

  return (
    <>
      <SectionCard title={t("admin_add_user")} hint={t("admin_add_user_hint")}>
        <div className="grid gap-3 md:grid-cols-4">
          <input className={inputClass} placeholder="name@example.com" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <select className={inputClass} value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="phc_operator">{t("health_worker")}</option>
            <option value="district_admin">{t("district_officer")}</option>
            <option value="super_admin">{t("admin_role_super")}</option>
          </select>
          {form.role === "phc_operator" && (
            <select className={inputClass} value={form.centre_id}
              onChange={(e) => setForm({ ...form, centre_id: e.target.value })}>
              <option value="">{t("which_centre")}</option>
              {centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          )}
          {form.role === "district_admin" && (
            <select className={inputClass} value={form.district_id}
              onChange={(e) => setForm({ ...form, district_id: e.target.value })}>
              <option value="">{t("admin_pick_district")}</option>
              {districts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          )}
          <button onClick={save} disabled={busy || !form.email}
            className="rounded-action bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {t("admin_save_user")}
          </button>
        </div>
        {msg && <p className={`mt-3 text-sm ${msg.ok ? "text-brand" : "text-critical"}`}>{msg.text}</p>}
      </SectionCard>

      <SectionCard title={t("admin_tab_users")}>
        {users === null ? <p className="text-ink-muted">{t("generating")}</p> : (
          <div className="divide-y divide-line-light">
            {users.map((u) => (
              <div key={u.email} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <div className="font-semibold">{u.email}</div>
                  <div className="text-sm text-ink-muted">
                    {roleLabel[u.role] || u.role}
                    {u.centre_id ? ` · ${u.centre_id}` : ""}
                    {u.signed_in === false ? ` · ${t("admin_never_signed_in")}` : ""}
                  </div>
                </div>
                <button onClick={() => remove(u.email)}
                  className="rounded-action border border-line-control px-3 py-1.5 text-sm text-critical">
                  {t("admin_remove")}
                </button>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </>
  );
}

/* ---------------- districts ---------------- */

function DistrictsTab() {
  const { t } = useLang();
  const [overview, setOverview] = useState(null);
  const [form, setForm] = useState({ name: "", state: "" });
  const [msg, setMsg] = useState(null);

  const refresh = () =>
    api.get("/api/admin/overview")
      .then((d) => setOverview(d?.districts ? d : { districts: [] }))
      .catch(() => setOverview({ districts: [] }));
  useEffect(() => { refresh(); }, []);

  async function create() {
    setMsg(null);
    try {
      await api.post("/api/admin/districts", form);
      setForm({ name: "", state: "" });
      setMsg({ ok: true, text: t("admin_district_created") });
      refresh();
    } catch (e) { setMsg({ ok: false, text: e?.detail || t("admin_failed") }); }
  }

  return (
    <>
      <SectionCard title={t("admin_add_district")} hint={t("admin_add_district_hint")}>
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
      </SectionCard>

      <SectionCard title={t("admin_tab_districts")}>
        {overview === null ? <p className="text-ink-muted">{t("generating")}</p> : (
          <div className="divide-y divide-line-light">
            {overview.districts.map((d) => (
              <div key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <div className="font-semibold">{d.name}</div>
                  <div className="text-sm text-ink-muted">
                    {d.state} · {d.centres} {t("all_centres").toLowerCase()} · {d.default_language.toUpperCase()}
                  </div>
                </div>
                <Link to={`/reports?district=${d.id}`}
                  className="rounded-action border border-line-control px-3 py-1.5 text-sm">
                  {t("reports_title")}
                </Link>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </>
  );
}

/* ---------------- per-centre medicines ---------------- */

function MedicinesTab() {
  const { t, local } = useLang();
  const [centres, setCentres] = useState([]);
  const [centreId, setCentreId] = useState("");
  const [meds, setMeds] = useState(null);
  const [form, setForm] = useState({ name: "", unit: "tablets" });
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    api.get("/api/admin/centres-list").then((d) => setCentres(d.centres || [])).catch(() => {});
  }, []);

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
    <SectionCard title={t("admin_tab_medicines")} hint={t("admin_medicines_hint")}>
      <select className={inputClass + " max-w-md"} value={centreId}
        onChange={(e) => setCentreId(e.target.value)}>
        <option value="">{t("which_centre")}</option>
        {centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>

      {centreId && meds === null && <p className="mt-4 text-ink-muted">{t("generating")}</p>}
      {centreId && meds && (
        <>
          <div className="mt-4 divide-y divide-line-light">
            {meds.map((m) => (
              <div key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-40">
                  <div className="font-semibold">{local("meds", m.medicine_name) || m.medicine_name}</div>
                  <div className="text-sm text-ink-muted">{local("units", m.unit)}</div>
                </div>
                <div className="flex items-center gap-5">
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
                    className="rounded-action border border-line-control px-3 py-1.5 text-sm text-critical">
                    {t("admin_remove")}
                  </button>
                </div>
              </div>
            ))}
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
    </SectionCard>
  );
}

/* ---------------- audit trail ---------------- */

function ActivityTab() {
  const { t } = useLang();
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    api.get("/api/admin/audit?limit=50").then((d) => setEntries(d.entries || [])).catch(() => setEntries([]));
  }, []);

  return (
    <SectionCard title={t("admin_tab_activity")} hint={t("admin_activity_hint")}>
      {entries === null ? <p className="text-ink-muted">{t("generating")}</p> : (
        <div className="divide-y divide-line-light text-sm">
          {entries.map((e) => (
            <div key={e.id} className="py-2.5">
              <span className="font-semibold">{e.actor?.email || e.actor?.uid || "—"}</span>
              <span className="text-ink-muted"> · {e.action} · {e.centre_id}</span>
              <span className="block text-xs text-ink-muted">{String(e.at).slice(0, 19).replace("T", " ")}</span>
            </div>
          ))}
          {entries.length === 0 && <p className="text-ink-muted">—</p>}
        </div>
      )}
    </SectionCard>
  );
}
