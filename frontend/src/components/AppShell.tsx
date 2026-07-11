"use client";

import { ReactNode, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, Users, Armchair, FolderKanban, Sparkles, LogOut } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/employees", label: "Employees", icon: Users },
  { href: "/seats", label: "Seats", icon: Armchair },
  { href: "/assistant", label: "AI Assistant", icon: Sparkles },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "var(--color-text-secondary)" }}>Loading…</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 220,
          borderRight: "1px solid var(--color-border)",
          background: "var(--color-surface)",
          padding: "24px 16px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ marginBottom: 32, paddingLeft: 8 }}>
          <div className="mono" style={{ fontSize: 12, letterSpacing: "0.08em", color: "var(--color-accent)" }}>
            ETHARA AI
          </div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 2 }}>Seat Allocation</div>
        </div>

        <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "9px 10px",
                  borderRadius: 8,
                  fontSize: 14,
                  textDecoration: "none",
                  color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                  background: isActive ? "var(--color-surface-raised)" : "transparent",
                }}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: 16, marginTop: 16 }}>
          <div style={{ fontSize: 13, color: "var(--color-text-primary)" }}>{user.full_name}</div>
          <div className="mono" style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 10 }}>
            {user.role.toUpperCase()}
          </div>
          <button
            onClick={logout}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "none",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              padding: "8px 10px",
              color: "var(--color-text-secondary)",
              fontSize: 13,
              cursor: "pointer",
              width: "100%",
            }}
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: 32, maxWidth: 1400 }}>{children}</main>
    </div>
  );
}
