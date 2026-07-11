"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { employeeService } from "@/services/api";

export default function EmployeesPage() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [onlyWithoutSeat, setOnlyWithoutSeat] = useState(false);
  const pageSize = 15;

  const { data, isLoading } = useQuery({
    queryKey: ["employees", query, page, onlyWithoutSeat],
    queryFn: () =>
      onlyWithoutSeat
        ? employeeService.withoutSeat({ page, page_size: pageSize })
        : employeeService.list({ q: query || undefined, page, page_size: pageSize }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <AppShell>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Employees</h1>
      <p style={{ color: "var(--color-text-secondary)", fontSize: 14, marginBottom: 20 }}>
        {data ? `${data.total.toLocaleString()} employees` : "Loading…"}
      </p>

      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <div style={{ position: "relative", flex: 1, maxWidth: 360 }}>
          <Search
            size={15}
            style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)" }}
          />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Search by name, employee code, or email…"
            disabled={onlyWithoutSeat}
            style={{
              width: "100%",
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              padding: "9px 12px 9px 34px",
              color: "var(--color-text-primary)",
              fontSize: 13,
              opacity: onlyWithoutSeat ? 0.5 : 1,
            }}
          />
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--color-text-secondary)", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={onlyWithoutSeat}
            onChange={(e) => {
              setOnlyWithoutSeat(e.target.checked);
              setPage(1);
            }}
          />
          New joiners without a seat
        </label>
      </div>

      <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left" }}>
              {["Code", "Name", "Designation", "Status", "Location", "Joined"].map((h) => (
                <th key={h} style={{ padding: "10px 16px", color: "var(--color-text-secondary)", fontWeight: 500 }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} style={{ padding: 20, textAlign: "center", color: "var(--color-text-muted)" }}>
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 20, textAlign: "center", color: "var(--color-text-muted)" }}>
                  No employees found.
                </td>
              </tr>
            )}
            {data?.items.map((emp) => (
              <tr key={emp.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td className="mono" style={{ padding: "10px 16px", color: "var(--color-text-muted)" }}>
                  {emp.employee_code}
                </td>
                <td style={{ padding: "10px 16px" }}>{emp.full_name}</td>
                <td style={{ padding: "10px 16px", color: "var(--color-text-secondary)" }}>{emp.designation}</td>
                <td style={{ padding: "10px 16px" }}>
                  <StatusBadge status={emp.employment_status} />
                </td>
                <td style={{ padding: "10px 16px", color: "var(--color-text-secondary)" }}>{emp.location || "—"}</td>
                <td className="mono" style={{ padding: "10px 16px", color: "var(--color-text-muted)" }}>
                  {emp.date_of_joining}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > 0 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            Page {page} of {totalPages}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <PageButton disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </PageButton>
            <PageButton disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </PageButton>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "#4ADE80",
    on_leave: "#60A5FA",
    notice_period: "#E8A33D",
    terminated: "#EF4444",
  };
  const color = colors[status] || "#9498A8";
  return (
    <span
      style={{
        fontSize: 11,
        padding: "3px 8px",
        borderRadius: 999,
        color,
        background: `${color}20`,
        textTransform: "capitalize",
      }}
    >
      {status.replace("_", " ")}
    </span>
  );
}

function PageButton({ children, disabled, onClick }: { children: React.ReactNode; disabled: boolean; onClick: () => void }) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      style={{
        background: "var(--color-surface-raised)",
        border: "1px solid var(--color-border)",
        borderRadius: 6,
        padding: "6px 14px",
        color: disabled ? "var(--color-text-muted)" : "var(--color-text-primary)",
        fontSize: 13,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {children}
    </button>
  );
}
