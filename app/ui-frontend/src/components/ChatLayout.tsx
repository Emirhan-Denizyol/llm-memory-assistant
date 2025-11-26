// src/components/ChatLayout.tsx

import React from "react";
import type { ChatMessage, ChatSource } from "../api/types";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";

interface ChatLayoutProps {
  messages: ChatMessage[];
  sources: ChatSource[];
  loading: boolean;
  error: string | null;
  onSend: (text: string) => void;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({
  messages,
  sources,
  loading,
  error,
  onSend
}) => {
  return (
    <div className="chat-layout">
      <div className="chat-main">
        <MessageList messages={messages} loading={loading} sources={sources} />
        {error && <div className="error-banner">{error}</div>}
        <MessageInput onSend={onSend} disabled={loading} />
      </div>
    </div>
  );
};

export default ChatLayout;
