"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  InviteUserPayload,
  SmtpProvider,
  SmtpSettings,
  SmtpSettingsUpdate,
  UserListItem,
  UserProfile,
} from "@/lib/types";

const inputClass =
  "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-faint focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition";
const labelClass = "block text-xs font-medium text-muted mb-1";

function Banner({ msg, kind, onClose }: { msg: string; kind: "ok" | "err"; onClose: () => void }) {
  if (!msg) return null;
  const cls = kind === "ok" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-red-500/10 border-red-500/30 text-red-400";
  return (
    <div className={`border rounded-lg px-4 py-3 text-sm flex items-center justify-between ${cls}`}>
      <span>{msg}</span>
      <button onClick={onClose} className="ml-4 opacity-70 hover:opacity-100">✕</button>
    </div>
  );
}

/* ------------------------------- Profile tab ------------------------------ */
function ProfileTab({ profile, onSaved }: { profile: UserProfile; onSaved: () => void }) {
  const [firstName, setFirstName] = useState(profile.first_name ?? "");
  const [lastName, setLastName] = useState(profile.last_name ?? "");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [kind, setKind] = useState<"ok" | "err">("ok");

  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);

  async function saveProfile() {
    setSaving(true);
    setMsg("");
    try {
      await api.patch(`/auth/update-profile/${profile.id}`, { first_name: firstName, last_name: lastName });
      setKind("ok");
      setMsg("Profile updated");
      onSaved();
    } catch (e: unknown) {
      setKind("err");
      setMsg((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Update failed");
    } finally {
      setSaving(false);
    }
  }

  async function changePassword() {
    setPwSaving(true);
    setMsg("");
    try {
      await api.patch(`/auth/change-password`, {
        current_password: curPw,
        new_password: newPw,
        confirm_password: confirmPw,
      });
      setKind("ok");
      setMsg("Password changed");
      setCurPw(""); setNewPw(""); setConfirmPw("");
    } catch (e: unknown) {
      setKind("err");
      setMsg((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Password change failed");
    } finally {
      setPwSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-xl">
      <Banner msg={msg} kind={kind} onClose={() => setMsg("")} />

      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Profile</h2>
        <div>
          <label className={labelClass}>Email</label>
          <input value={profile.email} disabled className={`${inputClass} opacity-60`} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>First name</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Last name</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} className={inputClass} />
          </div>
        </div>
        <div className="flex justify-end">
          <button onClick={saveProfile} disabled={saving} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg">
            {saving ? "Saving…" : "Save profile"}
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Change password</h2>
        <div>
          <label className={labelClass}>Current password</label>
          <input type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} className={inputClass} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>New password</label>
            <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Confirm new password</label>
            <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} className={inputClass} />
          </div>
        </div>
        <div className="flex justify-end">
          <button onClick={changePassword} disabled={pwSaving || !curPw || !newPw} className="cursor-pointer border border-border text-foreground hover:bg-hover disabled:opacity-50 text-sm px-4 py-2 rounded-lg">
            {pwSaving ? "Updating…" : "Update password"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------- SMTP tab -------------------------------- */
function SmtpTab() {
  const [providers, setProviders] = useState<SmtpProvider[]>([]);
  const [providerId, setProviderId] = useState("custom");
  const [host, setHost] = useState("");
  const [port, setPort] = useState<number | "">("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordSet, setPasswordSet] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [fromEmail, setFromEmail] = useState("");
  const [fromName, setFromName] = useState("");
  const [imapHost, setImapHost] = useState("");
  const [imapPort, setImapPort] = useState<number | "">("");
  const [replyScan, setReplyScan] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [msg, setMsg] = useState("");
  const [kind, setKind] = useState<"ok" | "err">("ok");

  useEffect(() => {
    api.get<{ data: SmtpProvider[] }>("/auth/smtp/providers").then((r) => setProviders(r.data.data)).catch(() => {});
    api.get<{ data: SmtpSettings }>("/auth/smtp").then((r) => {
      const s = r.data.data;
      setHost(s.smtp_host ?? "");
      setPort(s.smtp_port ?? "");
      setUsername(s.smtp_username ?? "");
      setFromEmail(s.smtp_from_email ?? "");
      setFromName(s.smtp_from_name ?? "");
      setPasswordSet(!!s.password_set);
      setImapHost(s.imap_host ?? "");
      setImapPort(s.imap_port ?? "");
      setReplyScan(!!s.reply_scan_enabled);
    }).catch(() => {});
  }, []);

  function onProviderChange(id: string) {
    setProviderId(id);
    const p = providers.find((x) => x.id === id);
    if (p && id !== "custom") {
      setHost(p.host);
      setPort(p.port);
      setImapHost(p.imap_host ?? "");
      setImapPort(p.imap_port ?? "");
    }
  }

  async function reveal() {
    if (showPw) {
      setShowPw(false);
      return;
    }
    try {
      const r = await api.get<{ data: SmtpSettings }>("/auth/smtp?reveal=true");
      setPassword(r.data.data.smtp_password ?? "");
      setShowPw(true);
    } catch {
      setKind("err");
      setMsg("Could not reveal password");
    }
  }

  async function save() {
    setSaving(true);
    setMsg("");
    try {
      const payload: SmtpSettingsUpdate = {
        smtp_host: host || undefined,
        smtp_port: port === "" ? undefined : Number(port),
        smtp_username: username || undefined,
        smtp_from_email: fromEmail || undefined,
        smtp_from_name: fromName || undefined,
        imap_host: imapHost || undefined,
        imap_port: imapPort === "" ? undefined : Number(imapPort),
        reply_scan_enabled: replyScan,
      };
      if (password) payload.smtp_password = password; // only send when changed
      const r = await api.put<{ data: SmtpSettings }>("/auth/smtp", payload);
      setPasswordSet(!!r.data.data.password_set);
      setKind("ok");
      setMsg("SMTP settings saved");
    } catch (e: unknown) {
      setKind("err");
      setMsg((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function test() {
    setTesting(true);
    setMsg("");
    try {
      const r = await api.post<{ message: string }>("/auth/smtp/test");
      setKind("ok");
      setMsg(r.data.message || "Test email sent");
    } catch (e: unknown) {
      setKind("err");
      setMsg((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Test failed");
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="space-y-4 max-w-xl">
      <Banner msg={msg} kind={kind} onClose={() => setMsg("")} />
      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <div>
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Email (SMTP)</h2>
          <p className="text-xs text-faint mt-0.5">Your campaigns send from this account. Password is stored encrypted.</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>Provider</label>
            <select value={providerId} onChange={(e) => onProviderChange(e.target.value)} className={inputClass}>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Port</label>
            <input type="number" value={port} onChange={(e) => setPort(e.target.value === "" ? "" : Number(e.target.value))} disabled={providerId !== "custom"} className={`${inputClass} ${providerId !== "custom" ? "opacity-60" : ""}`} />
          </div>
        </div>

        <div>
          <label className={labelClass}>SMTP host</label>
          <input value={host} onChange={(e) => setHost(e.target.value)} disabled={providerId !== "custom"} className={`${inputClass} ${providerId !== "custom" ? "opacity-60" : ""}`} placeholder="smtp.gmail.com" />
        </div>

        <div>
          <label className={labelClass}>Username / email</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} className={inputClass} placeholder="you@gmail.com" />
        </div>

        <div>
          <label className={labelClass}>Password {passwordSet && <span className="text-faint">(saved — leave blank to keep)</span>}</label>
          <div className="flex gap-2">
            <input type={showPw ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} placeholder={passwordSet ? "••••••••" : "App password"} />
            <button type="button" onClick={reveal} className="cursor-pointer border border-border text-muted hover:text-foreground text-xs px-3 rounded-lg flex-shrink-0">
              {showPw ? "Hide" : "Reveal"}
            </button>
          </div>
          <p className="text-xs text-faint mt-1">For Gmail/Zoho use an app-specific password.</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>From email</label>
            <input value={fromEmail} onChange={(e) => setFromEmail(e.target.value)} className={inputClass} placeholder="defaults to username" />
          </div>
          <div>
            <label className={labelClass}>From name</label>
            <input value={fromName} onChange={(e) => setFromName(e.target.value)} className={inputClass} placeholder="Your Name" />
          </div>
        </div>

        <div className="border-t border-border pt-4 mt-1 space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={replyScan}
              onChange={(e) => setReplyScan(e.target.checked)}
              className="mt-0.5 rounded border-border"
            />
            <span>
              <span className="text-sm text-foreground">Enable reply detection (IMAP)</span>
              <span className="block text-xs text-faint">
                Periodically checks your inbox for replies, marks the lead as Responded, and auto-stops follow-ups to anyone who replied.
              </span>
            </span>
          </label>

          {replyScan && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>IMAP host</label>
                <input value={imapHost} onChange={(e) => setImapHost(e.target.value)} disabled={providerId !== "custom"} className={`${inputClass} ${providerId !== "custom" ? "opacity-60" : ""}`} placeholder="imap.gmail.com" />
              </div>
              <div>
                <label className={labelClass}>IMAP port</label>
                <input type="number" value={imapPort} onChange={(e) => setImapPort(e.target.value === "" ? "" : Number(e.target.value))} disabled={providerId !== "custom"} className={`${inputClass} ${providerId !== "custom" ? "opacity-60" : ""}`} />
              </div>
              <p className="col-span-2 text-xs text-faint">Login reuses the SMTP username and password above.</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={test} disabled={testing} className="cursor-pointer border border-border text-foreground hover:bg-hover disabled:opacity-50 text-sm px-4 py-2 rounded-lg">
            {testing ? "Sending…" : "Send test email"}
          </button>
          <button onClick={save} disabled={saving} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg">
            {saving ? "Saving…" : "Save SMTP"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------- Team tab -------------------------------- */
function TeamTab() {
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("user");
  const [inviting, setInviting] = useState(false);
  const [msg, setMsg] = useState("");
  const [kind, setKind] = useState<"ok" | "err">("ok");
  const [tempPw, setTempPw] = useState("");

  function loadUsers() {
    api.get<{ data: UserListItem[] }>("/auth/users").then((r) => setUsers(r.data.data)).catch(() => {});
  }
  useEffect(loadUsers, []);

  async function invite() {
    setInviting(true);
    setMsg("");
    setTempPw("");
    try {
      const payload: InviteUserPayload = { email, first_name: firstName || undefined, last_name: lastName || undefined, role };
      const r = await api.post<{ data: { temp_password?: string } }>("/auth/users", payload);
      setKind("ok");
      setMsg(`Invited ${email}`);
      if (r.data.data?.temp_password) setTempPw(r.data.data.temp_password);
      setEmail(""); setFirstName(""); setLastName(""); setRole("user");
      loadUsers();
    } catch (e: unknown) {
      setKind("err");
      setMsg((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Invite failed");
    } finally {
      setInviting(false);
    }
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <Banner msg={msg} kind={kind} onClose={() => setMsg("")} />
      {tempPw && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3 text-sm text-indigo-300">
          Temporary password (share securely, shown once): <code className="font-mono text-foreground">{tempPw}</code>
        </div>
      )}

      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Invite user</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={labelClass}>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} placeholder="teammate@example.com" />
          </div>
          <div>
            <label className={labelClass}>First name</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Last name</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className={inputClass}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
        <div className="flex justify-end">
          <button onClick={invite} disabled={inviting || !email} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg">
            {inviting ? "Inviting…" : "Invite user"}
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="p-4 border-b border-border text-sm font-medium text-muted">Users ({users.length})</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-subtle uppercase tracking-wide">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Role</th>
              <th className="px-4 py-2 font-medium">Last login</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {users.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-2 text-foreground">{[u.first_name, u.last_name].filter(Boolean).join(" ") || "—"}</td>
                <td className="px-4 py-2 text-muted">{u.email}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${u.role === "admin" ? "bg-indigo-500/15 text-indigo-400" : "bg-hover text-muted"}`}>{u.role}</span>
                </td>
                <td className="px-4 py-2 text-subtle text-xs">{u.last_loggedin_at ? new Date(u.last_loggedin_at).toLocaleDateString() : "never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* -------------------------------- Page shell ------------------------------ */
function SettingsInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "profile";
  const [profile, setProfile] = useState<UserProfile | null>(null);

  function loadProfile() {
    api.get<{ data: UserProfile }>("/auth/get-profile").then((r) => setProfile(r.data.data)).catch(() => {});
  }
  useEffect(loadProfile, []);

  const isAdmin = profile?.role === "admin";
  const tabs = [
    { id: "profile", label: "Profile" },
    { id: "smtp", label: "Email (SMTP)" },
    ...(isAdmin ? [{ id: "team", label: "Team" }] : []),
  ];

  function go(id: string) {
    router.push(id === "profile" ? "/settings" : `/settings?tab=${id}`);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-subtle mt-0.5">Manage your profile, email sending, and team</p>
      </div>

      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => go(t.id)}
            className={`cursor-pointer px-4 py-2 text-sm border-b-2 -mb-px transition ${
              tab === t.id ? "border-indigo-500 text-foreground" : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "profile" && profile && <ProfileTab profile={profile} onSaved={loadProfile} />}
      {tab === "smtp" && <SmtpTab />}
      {tab === "team" && isAdmin && <TeamTab />}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="text-subtle">Loading…</div>}>
      <SettingsInner />
    </Suspense>
  );
}
