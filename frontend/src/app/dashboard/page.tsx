"use client";

import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { AppShell } from "@/components/AppShell";
import { StatCard, Panel } from "@/components/StatCard";
import { dashboardService } from "@/services/api";

const PIE_COLORS = ["#E8A33D", "#4ADE80", "#60A5FA", "#6B7280"];

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardService.summary,
  });

  return (
    <AppShell>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Dashboard</h1>
      <p style={{ color: "var(--color-text-secondary)", fontSize: 14, marginBottom: 24 }}>
        Live occupancy and allocation overview across all buildings.
      </p>

      {isLoading && <p style={{ color: "var(--color-text-secondary)" }}>Loading dashboard…</p>}
      {error != null && (
        <p style={{ color: "var(--color-danger)" }}>Couldn&apos;t load dashboard data. Is the backend running?</p>
      )}

      {data && (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <StatCard label="Total Employees" value={data.total_employees.toLocaleString()} />
            <StatCard
              label="Occupied Seats"
              value={data.occupancy.occupied.toLocaleString()}
              accent="var(--color-occupied)"
            />
            <StatCard
              label="Vacant Seats"
              value={data.occupancy.vacant.toLocaleString()}
              accent="var(--color-vacant)"
            />
            <StatCard label="Utilization" value={`${data.occupancy.utilization_percent}%`} />
            <StatCard label="New Joiners (30d)" value={data.new_joiners_last_30_days} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <Panel title="Occupancy Breakdown">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={[
                      { name: "Occupied", value: data.occupancy.occupied },
                      { name: "Vacant", value: data.occupancy.vacant },
                      { name: "Reserved", value: data.occupancy.reserved },
                      { name: "Out of Service", value: data.occupancy.out_of_service },
                    ]}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={85}
                  >
                    {PIE_COLORS.map((c, i) => (
                      <Cell key={i} fill={c} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#1F222E", border: "1px solid #2A2E3D", borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            </Panel>

            <Panel title="Department-wise Headcount">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.department_wise.slice(0, 8)} layout="vertical" margin={{ left: 20 }}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="department" type="category" width={110} tick={{ fontSize: 11, fill: "#9498A8" }} />
                  <Tooltip contentStyle={{ background: "#1F222E", border: "1px solid #2A2E3D", borderRadius: 8 }} />
                  <Bar dataKey="count" fill="#E8A33D" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Panel>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Panel title="Recent Allocations">
              <ActivityList items={data.recent_allocations} kind="allocated" />
            </Panel>
            <Panel title="Recent Releases">
              <ActivityList items={data.recent_releases} kind="released" />
            </Panel>
          </div>
        </>
      )}
    </AppShell>
  );
}

function ActivityList({
  items,
  kind,
}: {
  items: { id: string; allocation_date: string; release_date: string | null }[];
  kind: "allocated" | "released";
}) {
  if (items.length === 0) {
    return <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>No recent activity.</p>;
  }
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
      {items.map((item) => (
        <li key={item.id} style={{ fontSize: 13, color: "var(--color-text-secondary)", display: "flex", justifyContent: "space-between" }}>
          <span>Seat {kind}</span>
          <span className="mono" style={{ color: "var(--color-text-muted)" }}>
            {kind === "allocated" ? item.allocation_date : item.release_date}
          </span>
        </li>
      ))}
    </ul>
  );
}
