// src/App.tsx

import React, { useEffect, useState } from "react";
import "./styles.css";
import ChatLayout from "./components/ChatLayout";
import Sidebar from "./components/Sidebar";
import type { ChatMessage, ChatSession, ChatSource } from "./api/types";
import {
  sendChatMessage,
  addLocalMemory,
  addGlobalMemory,
} from "./api/client";


const STORAGE_PREFIX = "jetlink_sessions_";

function loadSessions(userId: string): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + userId);
    if (!raw) return [];
    return JSON.parse(raw) as ChatSession[];
  } catch {
    return [];
  }
}

function saveSessions(userId: string, sessions: ChatSession[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    STORAGE_PREFIX + userId,
    JSON.stringify(sessions)
  );
}

function createSessionObject(): ChatSession {
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const now = Date.now();
  return {
    id,
    title: "Yeni sohbet",
    createdAt: now,
    updatedAt: now,
    messages: []
  };
}

const App: React.FC = () => {
  const [userId, setUserId] = useState("test_user");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? null;

  // userId değişince o kullanıcıya ait session'ları yükle
  useEffect(() => {
    const loaded = loadSessions(userId);
    setSessions(loaded);
    setActiveSessionId(loaded[0]?.id ?? null);
  }, [userId]);

  // Session listesi değiştiğinde localStorage'a yaz
  useEffect(() => {
    saveSessions(userId, sessions);
  }, [userId, sessions]);

  const handleNewSession = () => {
    const session = createSessionObject();
    const next = [session, ...sessions];
    setSessions(next);
    setActiveSessionId(session.id);
    setSources([]);
    setError(null);
  };

  const handleSelectSession = (id: string) => {
    setActiveSessionId(id);
    setSources([]);
    setError(null);
  };

  const handleDeleteSession = (id: string) => {
    const next = sessions.filter((s) => s.id !== id);
    setSessions(next);

    if (activeSessionId === id) {
      setActiveSessionId(next[0]?.id ?? null);
      setSources([]);
    }
  };

  const handleRenameSession = (id: string, title: string) => {
    const next = sessions.map((s) =>
      s.id === id ? { ...s, title, updatedAt: Date.now() } : s
    );
    setSessions(next);
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    // Aktif session yoksa otomatik oluştur
    let session = activeSession;
    if (!session) {
      session = createSessionObject();
      const nextSessions = [session, ...sessions];
      setSessions(nextSessions);
      setActiveSessionId(session.id);
    }

    const userMsg: ChatMessage = { role: "user", content: text };
    const updatedUserMessages = [...session.messages, userMsg];

    // Optimistik olarak kullanıcı mesajını ekranda göster
    setSessions((prev) =>
      prev.map((s) =>
        s.id === session!.id
          ? {
              ...s,
              messages: updatedUserMessages,
              updatedAt: Date.now(),
              title:
                s.title === "Yeni sohbet" && text
                  ? text.slice(0, 30)
                  : s.title,
            }
          : s,
      ),
    );
    setLoading(true);
    setError(null);

    try {
      // 1) Sohbet endpointi (STM + retrieval + cevap)
      const response = await sendChatMessage({
        user_id: userId,
        session_id: session.id,
        message: text,
        topk_local: 5,
        topk_global: 5,
        stm_max_turns: 8,
        return_sources: true,
      });

      const botMsg: ChatMessage = {
        role: "assistant",
        content: response.reply,
      };

      const fullMessages = [...updatedUserMessages, botMsg];

      // Ekrandaki mesajları güncelle
      setSessions((prev) =>
        prev.map((s) =>
          s.id === session!.id
            ? {
                ...s,
                messages: fullMessages,
                updatedAt: Date.now(),
              }
            : s,
        ),
      );
      setSources(response.sources || []);

      // 2) LTM: Bu turu Local ve Global LTM'e yaz (debug log'lu)
      const memoryText = `User: ${text}\nAssistant: ${response.reply}`.trim();
      const compact = memoryText.replace(/\s+/g, "");

      console.log("DEBUG: memoryText:", memoryText);
      console.log(
        "DEBUG: memoryText length (no spaces):",
        compact.length,
      );

      if (compact.length > 20) {
        const baseMeta = {
          source: "chat",
          session_id: session.id,
          session_title: session.title,
          created_from: "ui-auto",
        };

        console.log(
          "DEBUG: local/global memory writeback tetiklendi!",
          baseMeta,
        );

        // Local LTM
        addLocalMemory({
          scope: "local",
          user_id: userId,
          session_id: session.id,
          text: memoryText,
          meta: baseMeta,
        })
          .then(() => console.log("DEBUG: LOCAL LTM OK"))
          .catch((e) => console.log("DEBUG: LOCAL LTM FAIL", e));

        // Global LTM
        addGlobalMemory({
          scope: "global",
          user_id: userId,
          session_id: session.id,
          text: memoryText,
          meta: baseMeta,
        })
          .then(() => console.log("DEBUG: GLOBAL LTM OK"))
          .catch((e) => console.log("DEBUG: GLOBAL LTM FAIL", e));
      } else {
        console.log(
          "DEBUG: memoryText çok kısa olduğu için LTM yazılmadı.",
        );
      }
    } catch (err) {
      console.error(err);
      setError("Mesaj gönderilirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>Jetlink Memory Bot</h1>
        <div className="header-controls">
          <div className="field">
            <label>User ID</label>
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
        </div>
      </header>

      <div className="app-body">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
        />

        <main className="app-main">
          <div className="session-info">
            <div>
              <span className="session-label">Aktif session:</span>{" "}
              {activeSession ? activeSession.title : "Yok"}
            </div>
            <div>
              <span className="session-label">Session ID:</span>{" "}
              {activeSession ? activeSession.id : "—"}
            </div>
          </div>

          <ChatLayout
            messages={activeSession?.messages ?? []}
            sources={sources}
            loading={loading}
            error={error}
            onSend={handleSendMessage}
          />
        </main>
      </div>
    </div>
  );
};

export default App;
