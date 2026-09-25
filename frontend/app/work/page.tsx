"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useSession } from "@/components/session-provider";
import { addTaskMessage, approveWorkTask, createWorkTask, listAssistants, listTaskMessages, listWorkTasks, retryWorkTask, type EuniaAssistant, type TaskMessage, type WorkTask } from "@/lib/eunia-api";
import styles from "./page.module.css";

const liveStatuses = new Set(["queued", "in_progress"]);
const statusLabel: Record<string, string> = { queued: "Queued", in_progress: "In progress", awaiting_review: "Awaiting review", completed: "Completed", failed: "Needs attention" };
const initials = (name: string) => name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();

export default function WorkPage() {
  const { session } = useSession();
  const [employees, setEmployees] = useState<EuniaAssistant[]>([]);
  const [tasks, setTasks] = useState<WorkTask[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<TaskMessage[]>([]);
  const [filter, setFilter] = useState("all");
  const [employeeFilter, setEmployeeFilter] = useState("all");
  const [taskQuery, setTaskQuery] = useState("");
  const [modalEmployeeId, setModalEmployeeId] = useState("");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const selected = tasks.find((task) => task.id === selectedId) ?? null;
  const employee = employees.find((item) => item.id === selected?.assistant_id);

  async function refresh() {
    if (!session) return;
    const [work, people] = await Promise.all([listWorkTasks(session.token, session.workspace.id), listAssistants(session.token, session.workspace.id)]);
    setTasks(work); setEmployees(people);
    setSelectedId((current) => current && work.some((task) => task.id === current) ? current : work[0]?.id ?? null);
  }

  useEffect(() => {
    if (!session) return;
    refresh().then(() => { const requested = new URLSearchParams(window.location.search).get("employee"); if (requested) { setModalEmployeeId(requested); setEmployeeFilter(requested); setOpen(true); } }).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load work."));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  useEffect(() => {
    if (!session || !selectedId) { setMessages([]); return; }
    listTaskMessages(session.token, session.workspace.id, selectedId).then(setMessages).catch(() => setMessages([]));
  }, [selectedId, session, selected?.updated_at]);

  useEffect(() => {
    if (!session || !tasks.some((task) => liveStatuses.has(task.status))) return;
    const timer = window.setInterval(() => refresh().catch(() => undefined), 1500);
    return () => window.clearInterval(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, tasks]);

  const visible = useMemo(() => tasks.filter((task) => {
    const owner = employees.find((item) => item.id === task.assistant_id);
    const query = taskQuery.trim().toLowerCase();
    return (filter === "all" || task.status === filter) && (employeeFilter === "all" || task.assistant_id === employeeFilter) && (!query || [task.title, task.stage, owner?.name ?? "", owner?.role ?? "", owner?.department ?? ""].some((value) => value.toLowerCase().includes(query)));
  }), [employeeFilter, employees, filter, taskQuery, tasks]);
  const activeEmployees = useMemo(() => employees.filter((item) => item.status === "active"), [employees]);
  const departments = useMemo(() => Array.from(new Set(employees.map((item) => item.department))).sort(), [employees]);
  const modalEmployee = employees.find((item) => item.id === modalEmployeeId);
  const counts = { active: tasks.filter((task) => liveStatuses.has(task.status)).length, review: tasks.filter((task) => task.status === "awaiting_review").length, done: tasks.filter((task) => task.status === "completed").length };

  useEffect(() => {
    if (!selectedId || !visible.some((task) => task.id === selectedId)) setSelectedId(visible[0]?.id ?? null);
  }, [selectedId, visible]);

  async function submitTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session) return; setSaving(true); setError("");
    const form = event.currentTarget;
    const data = new FormData(form);
    const due = String(data.get("due") || "");
    try {
      const task = await createWorkTask(session.token, session.workspace.id, { assistant_id: String(data.get("assistant")), title: String(data.get("title")).trim(), instructions: String(data.get("instructions")).trim(), expected_output: String(data.get("expectedOutput") || "").trim() || null, priority: String(data.get("priority")) as WorkTask["priority"], due_at: due ? new Date(due).toISOString() : null });
      setTasks((items) => [task, ...items]); setSelectedId(task.id); setEmployeeFilter(task.assistant_id); setOpen(false); setModalEmployeeId(""); form.reset();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to assign the task."); }
    finally { setSaving(false); }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session || !selected) return; const form = event.currentTarget; const content = String(new FormData(form).get("message") || "").trim(); if (!content) return;
    try { const message = await addTaskMessage(session.token, session.workspace.id, selected.id, content); setMessages((items) => [...items, message]); form.reset(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to send your message."); }
  }

  async function act(action: "approve" | "retry") {
    if (!session || !selected) return;
    try { const updated = action === "approve" ? await approveWorkTask(session.token, session.workspace.id, selected.id) : await retryWorkTask(session.token, session.workspace.id, selected.id); setTasks((items) => items.map((task) => task.id === updated.id ? updated : task)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to update this task."); }
  }

  return <WorkspaceShell><section className={styles.heading}><div><p>AI WORK DESK</p><h1>Work together, with oversight</h1><span>Assign company work, follow progress, communicate, and approve every result.</span></div><button onClick={() => { setModalEmployeeId(employeeFilter === "all" ? "" : employeeFilter); setOpen(true); }}>+ Assign task</button></section>
    <section className={styles.metrics}><article><span>Running now</span><strong>{counts.active}</strong></article><article><span>Waiting for review</span><strong>{counts.review}</strong></article><article><span>Completed</span><strong>{counts.done}</strong></article><article className={styles.safety}><span>Governance</span><strong>Human approval on</strong><small>External actions remain drafts</small></article></section>
    {error && <p className={styles.error}>{error}</p>}
    <section className={styles.finder}><label><span>Find a task</span><input type="search" value={taskQuery} onChange={(event) => setTaskQuery(event.target.value)} placeholder="Search tasks, roles, or departments" /></label><label><span>AI employee</span><select value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)}><option value="all">All AI employees ({employees.length})</option>{departments.map((department) => <optgroup label={department} key={department}>{employees.filter((item) => item.department === department).map((item) => <option value={item.id} key={item.id}>{item.name} — {item.role}</option>)}</optgroup>)}</select></label></section>
    <nav className={styles.filters}>{[["all","All work"],["in_progress","In progress"],["awaiting_review","Review"],["completed","Completed"],["failed","Needs attention"]].map(([value,label]) => <button className={filter === value ? styles.activeFilter : ""} key={value} onClick={() => setFilter(value)}>{label}</button>)}</nav>
    <section className={styles.workspace}>
      <aside className={styles.taskList}>{visible.map((task) => { const owner = employees.find((item) => item.id === task.assistant_id); return <button className={`${styles.taskCard} ${task.id === selectedId ? styles.selectedTask : ""}`} key={task.id} onClick={() => setSelectedId(task.id)}><div><span className={styles[task.status]}>{statusLabel[task.status]}</span><small>{task.priority}</small></div><strong>{task.title}</strong><div className={styles.assignee}><b>{initials(owner?.name ?? "AI")}</b><p><strong>{owner?.name ?? "AI employee"}</strong><small>{owner?.role} · {owner?.department}</small></p></div><div className={styles.miniProgress}><i style={{ width: `${task.progress}%` }} /></div><em>{task.stage}</em></button>; })}{!visible.length && <div className={styles.empty}><span>✦</span><strong>No matching work</strong><p>Change the employee, status, or search filter.</p></div>}</aside>
      <main className={styles.desk}>{selected ? <><header className={styles.taskHeader}><div className={styles.employeeIdentity}><b>{initials(employee?.name ?? "AI")}</b><div><span>{employee?.department}</span><h2>{selected.title}</h2><p>Working with <strong>{employee?.name}</strong> · {employee?.role} · Supervisor: you</p></div></div><span className={styles[`${selected.status}Badge`]}>{statusLabel[selected.status]}</span></header>
        <section className={styles.progressPanel}><div><strong>{selected.stage}</strong><span>{selected.progress}%</span></div><div className={styles.progress}><i style={{ width: `${selected.progress}%` }} /></div><p>{selected.risk_level === "approval_required" ? "Approval required: this request includes an external or sensitive action. The AI will prepare a draft only." : "The AI employee is using approved workspace knowledge. A person reviews the result before completion."}</p></section>
        <section className={styles.brief}><div><span>Task brief</span><p>{selected.instructions}</p></div>{selected.expected_output && <div><span>Expected result</span><p>{selected.expected_output}</p></div>}</section>
        <section className={styles.thread}><h3>Task conversation</h3>{messages.map((message) => <article className={`${styles.message} ${styles[message.author_type]}`} key={message.id}><div><strong>{message.author_name}</strong><time>{new Date(message.created_at).toLocaleString()}</time></div><p>{message.content}</p></article>)}</section>
        {selected.status === "awaiting_review" && <div className={styles.reviewBar}><p><strong>Review required</strong><span>Confirm the result is accurate before closing this task.</span></p><button onClick={() => act("approve")}>Approve & complete</button></div>}
        {selected.status === "failed" && <div className={styles.reviewBar}><p><strong>Task needs attention</strong><span>Make sure Ollama is available, then try again.</span></p><button onClick={() => act("retry")}>Retry task</button></div>}
        <form className={styles.composer} onSubmit={sendMessage}><input name="message" aria-label="Message the task team" placeholder={`Message ${employee?.name ?? "the AI employee"} and your team…`} maxLength={12000}/><button>Send</button></form>
      </> : <div className={styles.noSelection}><span>✦</span><h2>Your AI work desk</h2><p>Select a task or assign new work to start collaborating.</p><button onClick={() => setOpen(true)}>Assign first task</button></div>}</main>
    </section>
    {open && <div className={styles.overlay} onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}><form className={styles.modal} onSubmit={submitTask}><header><div><p>NEW ASSIGNMENT</p><h2>Choose who will do this work</h2><span>Select the AI employee by name, role, and department before writing the brief.</span></div><button type="button" onClick={() => setOpen(false)}>×</button></header><label>Assign to<select name="assistant" required value={modalEmployeeId} onChange={(event) => setModalEmployeeId(event.target.value)}><option value="">Choose an active AI employee</option>{departments.map((department) => <optgroup label={department} key={department}>{activeEmployees.filter((item) => item.department === department).map((item) => <option key={item.id} value={item.id}>{item.name} — {item.role}</option>)}</optgroup>)}</select></label>{modalEmployee && <section className={styles.employeePreview}><b>{initials(modalEmployee.name)}</b><div><span>ASSIGNED AI EMPLOYEE</span><strong>{modalEmployee.name}</strong><p>{modalEmployee.role} · {modalEmployee.department}</p></div><em>Active</em></section>}<label>Task title<input name="title" required minLength={3} maxLength={180} placeholder="e.g. Analyse Q3 operating costs" /></label><label>Instructions<textarea name="instructions" required minLength={10} maxLength={12000} rows={5} placeholder="Explain what needs to be done, what information matters, and any boundaries." /></label><label>Expected result<textarea name="expectedOutput" maxLength={4000} rows={2} placeholder="e.g. A one-page management summary with three recommendations" /></label><div className={styles.formRow}><label>Priority<select name="priority" defaultValue="normal"><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label><label>Due date<input name="due" type="datetime-local" /></label></div><div className={styles.guardrail}>Sensitive actions are never executed automatically. The AI prepares a draft for human approval.</div>{error && <p className={styles.error}>{error}</p>}<footer><button type="button" onClick={() => setOpen(false)}>Cancel</button><button disabled={saving || !modalEmployee}>{saving ? "Assigning…" : modalEmployee ? `Assign to ${modalEmployee.name}` : "Choose an employee"}</button></footer></form></div>}
  </WorkspaceShell>;
}
