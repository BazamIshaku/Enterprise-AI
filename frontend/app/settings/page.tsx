"use client";
import { FormEvent, useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useSession } from "@/components/session-provider";
import { addMember, listMembers, listWorkspaces, type Workspace, type WorkspaceMember } from "@/lib/eunia-api";
import styles from "./page.module.css";

export default function SettingsPage() {
  const { session, startSession } = useSession();
  const [members, setMembers] = useState<WorkspaceMember[]>([]); const [workspaces, setWorkspaces] = useState<Workspace[]>([]); const [error, setError] = useState(""); const [adding, setAdding] = useState(false);
  useEffect(() => { if (!session) return; Promise.all([listMembers(session.token, session.workspace.id), listWorkspaces(session.token)]).then(([people, spaces]) => { setMembers(people); setWorkspaces(spaces); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load workspace settings.")); }, [session]);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!session) return; setAdding(true); setError(""); const form = event.currentTarget; const data = new FormData(form); try { const member = await addMember(session.token, session.workspace.id, String(data.get("email")), String(data.get("role")) as "member" | "admin"); setMembers((items) => [...items, member]); form.reset(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to add this employee."); } finally { setAdding(false); } }
  return <WorkspaceShell><section className={styles.heading}><p>WORKSPACE SETTINGS</p><h1>Company access</h1><span>Invite registered employees, assign administrators, and switch between companies you belong to.</span></section>
    {error && <p className={styles.error}>{error}</p>}
    <section className={styles.card}><div><span className={styles.logo}>{session?.workspace.name[0]}</span><div><h2>{session?.workspace.name}</h2><p>{session?.workspace.slug}</p></div></div>{workspaces.length > 1 && <select value={session?.workspace.id} onChange={(event) => { const workspace = workspaces.find((item) => item.id === event.target.value); if (workspace && session) startSession(session.token, workspace, session.user); }}><option disabled>Switch workspace</option>{workspaces.map((workspace) => <option value={workspace.id} key={workspace.id}>{workspace.name}</option>)}</select>}</section>
    <section className={`${styles.card} ${styles.membersCard}`}><div className={styles.memberHeading}><div><h2>Workspace members</h2><p>{members.length} {members.length === 1 ? "person has" : "people have"} access to AI employees and shared work.</p></div></div><form className={styles.invite} onSubmit={submit}><input aria-label="Employee email" name="email" type="email" required placeholder="employee@company.com"/><select name="role" aria-label="Access role"><option value="member">Employee</option><option value="admin">Administrator</option></select><button disabled={adding}>{adding ? "Adding…" : "Add employee"}</button></form><div className={styles.memberList}>{members.map((member) => <article key={member.id}><span>{member.full_name.split(" ").map((part) => part[0]).join("").slice(0,2)}</span><div><strong>{member.full_name}</strong><small>{member.email}</small></div><em>{member.role}</em></article>)}</div><p className={styles.hint}>For security, employees create their own account first. An administrator then adds their registered email to this company workspace.</p></section>
  </WorkspaceShell>;
}
