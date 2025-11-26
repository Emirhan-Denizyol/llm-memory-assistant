// src/components/Sidebar.tsx

import React from "react";
import type { ChatSession } from "../api/types";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onRenameSession
}) => {
  const handleRename = (id: string, currentTitle: string) => {
    const next = window.prompt("Yeni sohbet adı:", currentTitle);
    if (!next) return;
    onRenameSession(id, next);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="sidebar-new" onClick={onNewSession}>
          + Yeni sohbet
        </button>
      </div>

      <div className="sidebar-list">
        {sessions.length === 0 && (
          <div className="sidebar-empty">
            Henüz sohbet yok. Yeni sohbet başlatın.
          </div>
        )}

        {sessions.map((s) => (
          <div
            key={s.id}
            className={
              s.id === activeSessionId
                ? "sidebar-item active"
                : "sidebar-item"
            }
            onClick={() => onSelectSession(s.id)}
          >
            <div className="sidebar-item-main">
              <div className="sidebar-title">
                {s.title || "Adsız sohbet"}
              </div>
              <div className="sidebar-sub">
                {new Date(s.updatedAt).toLocaleTimeString()}
              </div>
            </div>
            <div className="sidebar-actions" onClick={(e) => e.stopPropagation()}>
              <button
                className="sidebar-icon-button"
                title="Yeniden adlandır"
                onClick={() => handleRename(s.id, s.title)}
              >
                ✏️
              </button>
              <button
                className="sidebar-icon-button"
                title="Sil"
                onClick={() => onDeleteSession(s.id)}
              >
                🗑
              </button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
};

export default Sidebar;
