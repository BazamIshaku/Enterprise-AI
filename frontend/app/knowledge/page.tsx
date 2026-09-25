"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useSession } from "@/components/session-provider";
import { listAssistants, listKnowledgeDocuments, retryKnowledgeDocument, uploadKnowledgeDocument, type EuniaAssistant, type KnowledgeDocument } from "@/lib/eunia-api";
import styles from "./page.module.css";

const acceptedTypes = ".pdf,.docx,.txt,.csv,.png,.jpg,.jpeg,.webp";
const formatSize = (bytes: number) => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const initials = (name: string) => name.split(" ").map((word) => word[0]).join("").slice(0, 2).toUpperCase();

export default function KnowledgePage() {
  const { session } = useSession();
  const [employees, setEmployees] = useState<EuniaAssistant[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [retryingId, setRetryingId] = useState("");

  useEffect(() => {
    if (!session) return;
    listAssistants(session.token, session.workspace.id).then((items) => { setEmployees(items); if (items[0]) setSelectedId(items[0].id); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load AI employees."));
  }, [session]);

  useEffect(() => {
    if (!session || !selectedId) return;
    listKnowledgeDocuments(session.token, session.workspace.id, selectedId).then(setDocuments).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load training files."));
  }, [selectedId, session]);

  useEffect(() => {
    if (!session || !selectedId || !documents.some((document) => document.status === "queued" || document.status === "processing")) return;
    const timer = window.setInterval(() => {
      listKnowledgeDocuments(session.token, session.workspace.id, selectedId).then(setDocuments).catch(() => undefined);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [documents, selectedId, session]);

  const selected = employees.find((employee) => employee.id === selectedId);
  const visibleDocuments = useMemo(() => documents.filter((document) => document.file_name.toLowerCase().includes(query.trim().toLowerCase())), [documents, query]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !session || !selected) return;
    setUploading(true); setError(""); setMessage("");
    try {
      const document = await uploadKnowledgeDocument(session.token, session.workspace.id, selected.id, file);
      setDocuments((items) => [document, ...items]);
      setMessage(`${file.name} was securely uploaded. ${selected.name} will review it and provide feedback when knowledge processing is complete.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to upload this file."); }
    finally { setUploading(false); }
  }

  async function retry(document: KnowledgeDocument) {
    if (!session || !selected) return;
    setRetryingId(document.id); setError("");
    try {
      const queued = await retryKnowledgeDocument(session.token, session.workspace.id, selected.id, document.id);
      setDocuments((items) => items.map((item) => item.id === queued.id ? queued : item));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to restart training."); }
    finally { setRetryingId(""); }
  }

  return <WorkspaceShell>
    <section className={styles.heading}><div><p>KNOWLEDGE & TRAINING</p><h1>Teach your AI workforce</h1><span>Assign confidential company knowledge to the employee who needs it.</span></div><div className={styles.secureBadge}><span>⌾</span><div><strong>Private by design</strong><small>Files stay inside this workspace</small></div></div></section>

    {!employees.length && !error ? <section className={styles.emptyState}><span>✦</span><h2>Create an AI employee first</h2><p>Employees appear here when they are ready to receive role-specific company knowledge.</p></section> : <div className={styles.workspace}>
      <aside className={styles.employeePanel}><div className={styles.panelTitle}><span>AI EMPLOYEES</span><strong>{employees.length}</strong></div>{employees.map((employee) => <button className={selectedId === employee.id ? styles.selectedEmployee : ""} key={employee.id} type="button" onClick={() => { setSelectedId(employee.id); setMessage(""); setError(""); }}><span className={styles.avatar}>{initials(employee.name)}</span><span><strong>{employee.name}</strong><small>{employee.role}</small></span><i>{selectedId === employee.id ? "●" : ""}</i></button>)}</aside>

      <section className={styles.trainingPanel}>
        {selected && <><header className={styles.employeeHeader}><div><span className={styles.avatarLarge}>{initials(selected.name)}</span><div><p>{selected.department}</p><h2>{selected.name}</h2><span>{selected.role}</span></div></div><span className={selected.status === "active" ? styles.active : styles.draft}>{selected.status}</span></header>
          <label className={`${styles.dropzone} ${uploading ? styles.uploading : ""}`}><input accept={acceptedTypes} disabled={uploading} onChange={upload} type="file" /><span className={styles.uploadIcon}>⇧</span><strong>{uploading ? "Securing your upload…" : "Add training material"}</strong><p>PDF, DOCX, TXT, CSV, PNG, JPG, or WEBP · maximum 10 MB</p><small>Files are validated and assigned only to {selected.name}.</small></label>
          {message && <div className={styles.confirmation}><span>✓</span><p><strong>Upload received</strong>{message}</p></div>}
          {error && <p className={styles.error}>{error}</p>}
          <div className={styles.libraryHeader}><div><h3>Training library</h3><span>{documents.length} {documents.length === 1 ? "file" : "files"}</span></div><label><span>⌕</span><input aria-label="Search training files" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search files" type="search" /></label></div>
          <div className={styles.fileList}>{visibleDocuments.map((document) => <article key={document.id}><span className={styles.fileIcon}>{document.content_type.startsWith("image/") ? "IMG" : document.file_name.split(".").pop()?.toUpperCase()}</span><div className={styles.fileDetails}><div className={styles.fileTitle}><div><h4>{document.file_name}</h4><p>{formatSize(document.size_bytes)} · Uploaded {new Date(document.created_at).toLocaleDateString()}</p></div><span className={`${styles.statusPill} ${styles[document.status]}`}><i />{document.status === "ready" ? "Training complete" : document.status === "failed" ? "Needs attention" : document.status === "processing" ? "Training" : "Queued"}</span></div><div className={styles.progressHeader}><span>{document.stage}</span><strong>{document.progress}%</strong></div><div className={styles.progressTrack} role="progressbar" aria-label={`Training progress for ${document.file_name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={document.progress}><span className={document.status === "failed" ? styles.failedBar : ""} style={{ width: `${document.progress}%` }} /></div><small>{document.feedback}</small>{document.status === "failed" && <button className={styles.retryButton} disabled={retryingId === document.id} type="button" onClick={() => retry(document)}>{retryingId === document.id ? "Restarting…" : "Retry training"}</button>}</div></article>)}{!visibleDocuments.length && <div className={styles.noFiles}><span>▱</span><p>{query ? "No files match your search." : `No training files have been assigned to ${selected.name} yet.`}</p></div>}</div>
        </>}
      </section>
    </div>}
  </WorkspaceShell>;
}
