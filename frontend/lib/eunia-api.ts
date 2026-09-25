export type TokenResponse = { access_token: string; token_type: "bearer" };
export type CurrentUser = { id: string; email: string; full_name: string };
export type Workspace = { id: string; name: string; slug: string; created_at: string };
export type Department = { id: string; name: string };
export type RoleTemplate = { id: string; department_id: string; name: string; description: string; capabilities: string[] };
export type EuniaAssistant = { id: string; workspace_id: string; name: string; role: string; department: string; role_template_id: string; status: "active" | "draft"; access_level: "admins_only" | "workspace"; capabilities: string[]; instructions: string | null; created_at: string; updated_at: string };
export type KnowledgeDocument = { id: string; workspace_id: string; assistant_id: string; file_name: string; content_type: string; size_bytes: number; status: "queued" | "processing" | "ready" | "failed"; stage: string; progress: number; chunk_count: number; processed_at: string | null; feedback: string; created_at: string };
export type Conversation = { id: string; workspace_id: string; title: string; created_at: string; updated_at: string };
export type NiaMessage = { id: string; conversation_id: string; role: "user" | "assistant"; content: string; created_at: string };
type Credentials = { email: string; password: string };

const apiBaseUrl = process.env.NEXT_PUBLIC_EUNIA_API_URL ?? "http://localhost:8000/api/v1";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail ?? "Something went wrong. Please try again."); }
  return response.json() as Promise<T>;
}
export function signIn(credentials: Credentials) { return request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(credentials) }); }
export function signUp(payload: Credentials & { full_name: string; workspace_name: string }) { return request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }); }
export function getCurrentUser(token: string) { return request<CurrentUser>("/auth/me", { headers: { Authorization: `Bearer ${token}` } }); }
export function requestPasswordReset(email: string) { return request<{ message: string }>("/auth/password-reset", { method: "POST", body: JSON.stringify({ email }) }); }
export function listWorkspaces(token: string) { return request<Workspace[]>("/workspaces", { headers: { Authorization: `Bearer ${token}` } }); }
export function listDepartments(token: string) { return request<Department[]>("/catalog/departments", { headers: { Authorization: `Bearer ${token}` } }); }
export function listRoleTemplates(token: string) { return request<RoleTemplate[]>("/catalog/roles", { headers: { Authorization: `Bearer ${token}` } }); }
export function listAssistants(token: string, workspaceId: string) { return request<EuniaAssistant[]>("/assistants", { headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function createAssistant(token: string, workspaceId: string, payload: Pick<EuniaAssistant, "name" | "role" | "department" | "role_template_id" | "status" | "access_level" | "capabilities" | "instructions">) { return request<EuniaAssistant>("/assistants", { method: "POST", body: JSON.stringify(payload), headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function updateAssistant(token: string, workspaceId: string, assistantId: string, payload: Pick<EuniaAssistant, "name" | "department" | "role_template_id" | "status" | "access_level" | "instructions">) { return request<EuniaAssistant>(`/assistants/${assistantId}`, { method: "PATCH", body: JSON.stringify(payload), headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function listKnowledgeDocuments(token: string, workspaceId: string, assistantId: string) { return request<KnowledgeDocument[]>(`/assistants/${assistantId}/knowledge`, { headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function uploadKnowledgeDocument(token: string, workspaceId: string, assistantId: string, file: File) { const body = new FormData(); body.append("file", file); return request<KnowledgeDocument>(`/assistants/${assistantId}/knowledge`, { method: "POST", body, headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function retryKnowledgeDocument(token: string, workspaceId: string, assistantId: string, documentId: string) { return request<KnowledgeDocument>(`/assistants/${assistantId}/knowledge/${documentId}/retry`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function createConversation(token: string, workspaceId: string) { return request<Conversation>("/conversations", { method: "POST", body: JSON.stringify({}), headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export function listMessages(token: string, workspaceId: string, conversationId: string) { return request<NiaMessage[]>(`/conversations/${conversationId}/messages`, { headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId } }); }
export async function streamNiaReply(token: string, workspaceId: string, conversationId: string, content: string, onDelta: (delta: string) => void) { const response = await fetch(`${apiBaseUrl}/conversations/${conversationId}/messages/stream`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId, "Content-Type": "application/json" }, body: JSON.stringify({ content }) }); if (!response.ok || !response.body) throw new Error("Unable to reach NIA."); const reader = response.body.getReader(); const decoder = new TextDecoder(); let pending = ""; while (true) { const { done, value } = await reader.read(); if (done) break; pending += decoder.decode(value, { stream: true }); const lines = pending.split("\n"); pending = lines.pop() ?? ""; for (const line of lines) { const data = line.trim().replace(/^data:\s*/, ""); if (!data || data === "[DONE]") continue; const message = JSON.parse(data) as { delta?: string; error?: string }; if (message.error) throw new Error(message.error); if (message.delta) onDelta(message.delta); } } }
