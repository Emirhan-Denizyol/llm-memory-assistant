import React, { useState } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const MessageInput: React.FC<Props> = ({ onSend, disabled }) => {
  const [value, setValue] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(e as any);
    }
  };

  return (
    <form className="message-input" onSubmit={submit}>
      <textarea
        placeholder="Mesaj yaz..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        Gönder
      </button>
    </form>
  );
};

export default MessageInput;
