import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <main style={{ margin: "0 auto", maxWidth: 1120, padding: "64px 24px" }}>
      <header style={{ marginBottom: 48 }}>
        <p style={{ color: "var(--primary)", fontWeight: 700, margin: 0 }}>ENTERPRISE AI</p>
        <h1 style={{ fontSize: 36, margin: "12px 0" }}>AI operations, built for your company.</h1>
        <p style={{ color: "var(--muted)", margin: 0 }}>
          A secure workspace for managing AI employees, knowledge, and enterprise workflows.
        </p>
      </header>
      {children}
    </main>
  );
}
