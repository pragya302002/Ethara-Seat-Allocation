"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { assistantService } from "@/services/api";
import { Send } from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

const EXAMPLE_QUESTIONS = [
  "Where is Eric Bernard sitting?",
  "How many empty seats are on Floor 2?",
  "List employees working for Acme Corp",
  "Who sits beside Eric Bernard?",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");

  const askMutation = useMutation({
    mutationFn: (question: string) => assistantService.ask(question),
    onSuccess: (data) => setMessages((m) => [...m, { role: "assistant", text: data.answer }]),
    onError: () =>
      setMessages((m) => [...m, { role: "assistant", text: "Something went wrong reaching the assistant. Try again." }]),
  });

  function send(question: string) {
    if (!question.trim()) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    askMutation.mutate(question);
    setInput("");
  }

  return (
    <AppShell>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>AI Assistant</h1>
      <p style={{ color: "var(--color-text-secondary)", fontSize: 14, marginBottom: 20 }}>
        Ask questions about employees, seats, and projects in plain language.
      </p>

      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: 12,
          padding: 20,
          minHeight: 380,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
          {messages.length === 0 && (
            <div>
              <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 12 }}>Try asking:</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    style={{
                      textAlign: "left",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--color-border)",
                      background: "var(--color-surface-raised)",
                      color: "var(--color-text-secondary)",
                      fontSize: 13,
                      cursor: "pointer",
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "75%",
                padding: "10px 14px",
                borderRadius: 10,
                fontSize: 14,
                background: msg.role === "user" ? "var(--color-accent-soft)" : "var(--color-surface-raised)",
                color: msg.role === "user" ? "var(--color-accent)" : "var(--color-text-primary)",
              }}
            >
              {msg.text}
            </div>
          ))}
          {askMutation.isPending && (
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Thinking…</div>
          )}
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Ask a question…"
            style={{
              flex: 1,
              padding: "10px 12px",
              borderRadius: 8,
              border: "1px solid var(--color-border)",
              background: "var(--color-bg)",
              color: "var(--color-text-primary)",
              fontSize: 14,
            }}
          />
          <button
            onClick={() => send(input)}
            disabled={askMutation.isPending}
            style={{
              padding: "10px 14px",
              borderRadius: 8,
              border: "none",
              background: "var(--color-accent)",
              color: "#1A1206",
              cursor: "pointer",
            }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </AppShell>
  );
}
