"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/hooks/useAuth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    setIsSubmitting(true);
    try {
      await login(values.email, values.password);
    } catch (err: any) {
      setServerError(err?.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "radial-gradient(circle at 20% 20%, rgba(232,163,61,0.06), transparent 40%), var(--color-bg)",
      }}
    >
      <div style={{ width: 380 }}>
        <div style={{ marginBottom: 40, textAlign: "center" }}>
          <div
            className="mono"
            style={{
              display: "inline-block",
              fontSize: 13,
              letterSpacing: "0.08em",
              color: "var(--color-accent)",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              padding: "4px 10px",
              marginBottom: 16,
            }}
          >
            ETHARA AI
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 600, margin: 0 }}>Seat Allocation System</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: 14, marginTop: 8 }}>
            Sign in to manage seating, projects, and occupancy.
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 12,
            padding: 28,
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          <div>
            <label style={labelStyle}>Email</label>
            <input {...register("email")} type="email" placeholder="you@company.com" style={inputStyle} />
            {errors.email && <p style={errorTextStyle}>{errors.email.message}</p>}
          </div>
          <div>
            <label style={labelStyle}>Password</label>
            <input {...register("password")} type="password" placeholder="••••••••" style={inputStyle} />
            {errors.password && <p style={errorTextStyle}>{errors.password.message}</p>}
          </div>

          {serverError && (
            <div
              style={{
                background: "var(--color-danger-soft)",
                color: "var(--color-danger)",
                fontSize: 13,
                padding: "8px 12px",
                borderRadius: 6,
              }}
            >
              {serverError}
            </div>
          )}

          <button type="submit" disabled={isSubmitting} style={buttonStyle}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p style={{ textAlign: "center", color: "var(--color-text-muted)", fontSize: 12, marginTop: 20 }}>
          Demo password for all seeded accounts: <span className="mono">Password123!</span>
        </p>
      </div>
    </main>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  color: "var(--color-text-secondary)",
  marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--color-surface-raised)",
  border: "1px solid var(--color-border)",
  borderRadius: 8,
  padding: "10px 12px",
  color: "var(--color-text-primary)",
  fontSize: 14,
  outline: "none",
};

const errorTextStyle: React.CSSProperties = {
  color: "var(--color-danger)",
  fontSize: 12,
  marginTop: 4,
};

const buttonStyle: React.CSSProperties = {
  background: "var(--color-accent)",
  color: "#1A1400",
  border: "none",
  borderRadius: 8,
  padding: "11px 0",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
  marginTop: 4,
};
