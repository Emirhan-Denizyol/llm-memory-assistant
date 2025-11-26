import React, { useRef, useEffect } from "react";
import type { ChatMessage, ChatSource } from "../api/types";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  sources: ChatSource[];
}

const MessageList: React.FC<Props> = ({ messages, loading, sources }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, sources]);

  return (
    <div className="message-list">
      {messages.map((m, index) => (
        <div
          key={index}
          className={`message-bubble ${m.role === "user" ? "message-user" : "message-assistant"}`}
        >
          <div className="message-role">{m.role}</div>
          <div className="message-content">{m.content}</div>
        </div>
      ))}

      {loading && (
        <div className="message-bubble message-assistant">
          <div className="message-role">assistant</div>
          <div className="message-content">Yazıyor...</div>
        </div>
      )}

      {sources.length > 0 && (
        <div className="sources-panel">
          <strong>Kullanılan Kaynaklar</strong>
          <ul>
            {sources.map((s) => (
              <li key={s.id}>
                <div>Scope: {s.scope}</div>
                <div>Score: {s.score.toFixed(4)}</div>
                <div>Snippet: {s.snippet}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
