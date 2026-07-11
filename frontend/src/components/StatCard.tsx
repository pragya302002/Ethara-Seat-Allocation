import { ReactNode } from "react";

export function StatCard({
  label,
  value,
  sublabel,
  accent,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  accent?: string;
}) {
  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 12,
        padding: "18px 20px",
        flex: 1,
        minWidth: 160,
      }}
    >
      <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, color: accent || "var(--color-text-primary)" }}>{value}</div>
      {sublabel && <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>{sublabel}</div>}
    </div>
  );
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 12,
        padding: 20,
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--color-text-primary)" }}>
        {title}
      </div>
      {children}
    </div>
  );
}
