"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useSession } from "@/components/session-provider";
import { createAssistant, listAssistants, listDepartments, listRoleTemplates, type Department, type EuniaAssistant, type RoleTemplate } from "@/lib/eunia-api";
import styles from "./page.module.css";

const colors = ["violet", "blue", "rose", "mint"] as const;
const initials = (name: string) => name.split(" ").map((word) => word[0]).join("").slice(0, 2).toUpperCase();

export default function AssistantsPage() {
  const { session } = useSession();
  const [roster, setRoster] = useState<EuniaAssistant[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [roles, setRoles] = useState<RoleTemplate[]>([]);
  const [departmentId, setDepartmentId] = useState("");
  const [roleId, setRoleId] = useState("");
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!session) return;
    Promise.all([listAssistants(session.token, session.workspace.id), listDepartments(session.token), listRoleTemplates(session.token)])
      .then(([employees, departmentCatalog, roleCatalog]) => { setRoster(employees); setDepartments(departmentCatalog); setRoles(roleCatalog); })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load the AI workforce."));
  }, [session]);

  const selectedDepartment = departments.find((item) => item.id === departmentId);
  const availableRoles = roles.filter((role) => role.department_id === departmentId);
  const selectedRole = roles.find((role) => role.id === roleId);
  const visibleRoster = useMemo(() => roster.filter((employee) => {
    const matchesDepartment = filter === "all" || employee.department === departments.find((item) => item.id === filter)?.name;
    const search = query.trim().toLowerCase();
    const matchesSearch = !search || [employee.name, employee.role, employee.department, ...employee.capabilities].some((value) => value.toLowerCase().includes(search));
    return matchesDepartment && matchesSearch;
  }), [departments, filter, query, roster]);

  function closeModal() { setOpen(false); setDepartmentId(""); setRoleId(""); setError(""); }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !selectedDepartment || !selectedRole) return;
    setSaving(true); setError("");
    const form = new FormData(event.currentTarget);
    try {
      const employee = await createAssistant(session.token, session.workspace.id, {
        name: String(form.get("name")).trim(),
        role: selectedRole.name,
        department: selectedDepartment.id,
        role_template_id: selectedRole.id,
        status: String(form.get("status")) as "active" | "draft",
        access_level: String(form.get("accessLevel")) as "admins_only" | "workspace",
        capabilities: selectedRole.capabilities,
        instructions: String(form.get("instructions") || "").trim() || null,
      });
      setRoster((items) => [employee, ...items]);
      closeModal();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to create this AI employee."); }
    finally { setSaving(false); }
  }

  return <WorkspaceShell>
    <section className={styles.header}>
      <div><p className={styles.eyebrow}>AI WORKFORCE</p><h1>AI Employees</h1><p>Create governed teammates with a defined department, role, knowledge, and access boundary.</p></div>
      <button className={styles.primaryButton} type="button" onClick={() => setOpen(true)}>+ Create AI employee</button>
    </section>

    <section className={styles.toolbar}>
      <label className={styles.search}><span aria-hidden="true">⌕</span><input aria-label="Search AI employees" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search people, roles, or skills" type="search" /></label>
      <span className={styles.count}>{visibleRoster.length} {visibleRoster.length === 1 ? "employee" : "employees"}</span>
    </section>

    <nav className={styles.departmentTabs} aria-label="Filter AI employees by department">
      <button className={filter === "all" ? styles.selectedTab : ""} type="button" onClick={() => setFilter("all")}>All departments</button>
      {departments.map((department) => <button className={filter === department.id ? styles.selectedTab : ""} key={department.id} type="button" onClick={() => setFilter(department.id)}>{department.name}</button>)}
    </nav>

    {error && !open && <p className={styles.error}>{error}</p>}
    <section className={styles.grid}>
      {visibleRoster.map((assistant, index) => <article className={styles.card} key={assistant.id}>
        <div className={styles.cardTopline}><div className={`${styles.avatar} ${styles[colors[index % colors.length]]}`}>{initials(assistant.name)}</div><span className={assistant.status === "active" ? styles.active : styles.draft}>{assistant.status === "active" ? "Active" : "Draft"}</span></div>
        <p className={styles.department}>{assistant.department}</p><h2>{assistant.name}</h2><p className={styles.role}>{assistant.role}</p>
        <div className={styles.capabilities}>{assistant.capabilities.slice(0, 3).map((capability) => <span key={capability}>{capability}</span>)}</div>
        <div className={styles.governance}><span>{assistant.access_level === "admins_only" ? "Admin managed" : "Workspace managed"}</span><span>Knowledge ready for upload</span></div>
        <button className={styles.manageButton} type="button">Manage employee <span>→</span></button>
      </article>)}
      {!visibleRoster.length && <div className={styles.empty}><span>✦</span><h2>No AI employees found</h2><p>Change the department or search, or create a new role-based employee.</p></div>}
      <button className={styles.createCard} type="button" onClick={() => setOpen(true)}><span>+</span><strong>Create an AI employee</strong><small>Choose a department and a governed starter role.</small></button>
    </section>

    {open && <div className={styles.overlay} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeModal(); }}>
      <form className={styles.modal} onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="create-title">
        <div className={styles.modalHeading}><div><p className={styles.eyebrow}>NEW AI EMPLOYEE</p><h2 id="create-title">Build a governed teammate</h2><p>Start with a proven role, then add company knowledge in the Knowledge workspace.</p></div><button type="button" aria-label="Close" onClick={closeModal}>×</button></div>
        <div className={styles.formGrid}>
          <label>Employee name<input name="name" required minLength={2} maxLength={120} placeholder="e.g. Aria" /></label>
          <label>Department<select required value={departmentId} onChange={(event) => { setDepartmentId(event.target.value); setRoleId(""); }}><option value="">Select a department</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
          <label className={styles.fullField}>Role template<select required disabled={!departmentId} value={roleId} onChange={(event) => setRoleId(event.target.value)}><option value="">{departmentId ? "Select a role" : "Choose a department first"}</option>{availableRoles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select></label>
        </div>
        {selectedRole && <section className={styles.rolePreview}><span>ROLE STARTER</span><h3>{selectedRole.name}</h3><p>{selectedRole.description}</p><div>{selectedRole.capabilities.map((capability) => <strong key={capability}>{capability}</strong>)}</div></section>}
        <label>Company instructions <small>Optional—do not include secrets here.</small><textarea name="instructions" maxLength={8000} rows={3} placeholder="Describe responsibilities, boundaries, and when this employee must escalate." /></label>
        <div className={styles.formGrid}><label>Initial status<select name="status"><option value="draft">Draft — training required</option><option value="active">Active</option></select></label><label>Who can change this employee?<select name="accessLevel"><option value="admins_only">Admins only</option><option value="workspace">Workspace members</option></select></label></div>
        <div className={styles.securityNote}><span>⌾</span><p><strong>Governed by default.</strong> Admin-only changes are recommended until knowledge and evaluation checks are complete.</p></div>
        {error && <p className={styles.error}>{error}</p>}
        <div className={styles.modalActions}><button type="button" onClick={closeModal}>Cancel</button><button className={styles.primaryButton} disabled={saving || !selectedRole} type="submit">{saving ? "Creating…" : "Create employee"}</button></div>
      </form>
    </div>}
  </WorkspaceShell>;
}
