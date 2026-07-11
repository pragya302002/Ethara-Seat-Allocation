"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { StatCard } from "@/components/StatCard";
import { seatService, employeeService, dashboardService } from "@/services/api";
import { Seat } from "@/types";

export default function SeatsPage() {
  const queryClient = useQueryClient();
  const [selectedSeat, setSelectedSeat] = useState<Seat | null>(null);
  const [employeeQuery, setEmployeeQuery] = useState("");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const { data: vacantSeats, isLoading } = useQuery({
    queryKey: ["vacant-seats"],
    queryFn: () => seatService.vacant(),
  });

  const { data: occupancy } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardService.summary,
  });

  const { data: employeeResults } = useQuery({
    queryKey: ["employee-search-for-allocation", employeeQuery],
    queryFn: () => employeeService.withoutSeat({ page: 1, page_size: 8 }),
    enabled: selectedSeat != null,
  });

  const allocateMutation = useMutation({
    mutationFn: (employeeId: string) =>
      seatService.allocate({ seat_id: selectedSeat!.id, employee_id: employeeId }),
    onSuccess: () => {
      setFeedback({ type: "success", text: `Seat ${selectedSeat?.seat_number} allocated.` });
      setSelectedSeat(null);
      queryClient.invalidateQueries({ queryKey: ["vacant-seats"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (err: any) => {
      setFeedback({ type: "error", text: err?.response?.data?.detail || "Allocation failed." });
    },
  });

  return (
    <AppShell>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Seats</h1>
      <p style={{ color: "var(--color-text-secondary)", fontSize: 14, marginBottom: 20 }}>
        Vacant seats available for allocation. Click a seat to assign it to a new joiner.
      </p>

      {occupancy && (
        <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
          <StatCard label="Vacant Now" value={occupancy.occupancy.available} accent="var(--color-vacant)" />
          <StatCard label="Occupied" value={occupancy.occupancy.occupied} accent="var(--color-occupied)" />
          <StatCard label="Utilization" value={`${occupancy.occupancy.utilization_percent}%`} />
        </div>
      )}

      {feedback && (
        <div
          style={{
            background: feedback.type === "success" ? "#1C2E1E" : "var(--color-danger-soft)",
            color: feedback.type === "success" ? "#4ADE80" : "var(--color-danger)",
            fontSize: 13,
            padding: "10px 14px",
            borderRadius: 8,
            marginBottom: 16,
          }}
        >
          {feedback.text}
        </div>
      )}

      {isLoading && <p style={{ color: "var(--color-text-secondary)" }}>Loading vacant seats…</p>}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(84px, 1fr))",
          gap: 8,
        }}
      >
        {vacantSeats?.slice(0, 200).map((seat) => (
          <button
            key={seat.id}
            onClick={() => setSelectedSeat(seat)}
            className="mono"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              padding: "10px 6px",
              fontSize: 11,
              color: "var(--color-vacant)",
              cursor: "pointer",
              textAlign: "center",
            }}
            title={`${seat.seat_type} seat${seat.bay ? " — " + seat.bay : ""}`}
          >
            <div>{seat.seat_number}</div>
            {seat.bay && (
              <div style={{ fontSize: 9, color: "var(--color-text-muted)", marginTop: 2 }}>{seat.bay}</div>
            )}
          </button>
        ))}
      </div>
      {vacantSeats && vacantSeats.length > 200 && (
        <p style={{ color: "var(--color-text-muted)", fontSize: 12, marginTop: 12 }}>
          Showing first 200 of {vacantSeats.length} vacant seats.
        </p>
      )}

      {selectedSeat && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onClick={() => setSelectedSeat(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 12,
              padding: 24,
              width: 400,
            }}
          >
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
              Allocate seat <span className="mono">{selectedSeat.seat_number}</span>
            </h3>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 16 }}>
              Choose a new joiner without a current seat:
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 260, overflowY: "auto" }}>
              {employeeResults?.items.length === 0 && (
                <p style={{ fontSize: 13, color: "var(--color-text-muted)" }}>No new joiners without a seat right now.</p>
              )}
              {employeeResults?.items.map((emp) => (
                <button
                  key={emp.id}
                  onClick={() => allocateMutation.mutate(emp.id)}
                  disabled={allocateMutation.isPending}
                  style={{
                    textAlign: "left",
                    background: "var(--color-surface-raised)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    padding: "10px 12px",
                    color: "var(--color-text-primary)",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  {emp.full_name} <span style={{ color: "var(--color-text-muted)" }}>— {emp.designation}</span>
                </button>
              ))}
            </div>
            <button
              onClick={() => setSelectedSeat(null)}
              style={{
                marginTop: 16,
                width: "100%",
                background: "none",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                padding: "9px 0",
                color: "var(--color-text-secondary)",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </AppShell>
  );
}