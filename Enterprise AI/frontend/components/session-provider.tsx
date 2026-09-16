"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getCurrentUser, listWorkspaces, type CurrentUser, type Workspace } from "@/lib/eunia-api";

type Session = { token: string; workspace: Workspace; user: CurrentUser };
type SessionContextValue = { session: Session | null; loading: boolean; startSession: (token: string, workspace: Workspace, user: CurrentUser) => void; signOut: () => void };
const SessionContext = createContext<SessionContextValue | undefined>(undefined);
const tokenKey = "eunia.accessToken";
const workspaceKey = "eunia.workspace";
const userKey = "eunia.user";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const token = localStorage.getItem(tokenKey);
    const savedWorkspace = localStorage.getItem(workspaceKey);
    const savedUser = localStorage.getItem(userKey);
    if (!token || !savedWorkspace || !savedUser) { setLoading(false); return; }
    try {
      const workspace = JSON.parse(savedWorkspace) as Workspace;
      const user = JSON.parse(savedUser) as CurrentUser;
      Promise.all([getCurrentUser(token), listWorkspaces(token)]).then(([currentUser, workspaces]) => {
        const currentWorkspace = workspaces.find((item) => item.id === workspace.id);
        if (!currentWorkspace) throw new Error("Workspace is no longer available");
        localStorage.setItem(workspaceKey, JSON.stringify(currentWorkspace));
        localStorage.setItem(userKey, JSON.stringify(currentUser));
        setSession({ token, workspace: currentWorkspace, user: currentUser });
      }).catch(() => {
        localStorage.removeItem(tokenKey); localStorage.removeItem(workspaceKey); localStorage.removeItem(userKey); localStorage.removeItem("eunia.workspaceId");
      }).finally(() => setLoading(false));
      return;
    } catch { localStorage.removeItem(tokenKey); localStorage.removeItem(workspaceKey); localStorage.removeItem(userKey); }
    setLoading(false);
  }, []);
  const value = useMemo(() => ({ session, loading, startSession: (token: string, workspace: Workspace, user: CurrentUser) => { localStorage.setItem(tokenKey, token); localStorage.setItem(workspaceKey, JSON.stringify(workspace)); localStorage.setItem(userKey, JSON.stringify(user)); localStorage.setItem("eunia.workspaceId", workspace.id); setSession({ token, workspace, user }); }, signOut: () => { localStorage.removeItem(tokenKey); localStorage.removeItem(workspaceKey); localStorage.removeItem(userKey); localStorage.removeItem("eunia.workspaceId"); setSession(null); } }), [session, loading]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
export function useSession() { const context = useContext(SessionContext); if (!context) throw new Error("useSession must be used inside SessionProvider"); return context; }

export async function workspaceForToken(token: string) { const workspaces = await listWorkspaces(token); if (!workspaces[0]) throw new Error("No workspace was found for this account."); return workspaces[0]; }
export function userForToken(token: string) { return getCurrentUser(token); }
