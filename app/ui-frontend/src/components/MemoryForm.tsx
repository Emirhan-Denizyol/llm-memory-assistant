// src/components/MemoryForm.tsx

import React, { useState } from "react";
import type { MemoryScope, MemoryRecord } from "../api/types";
import { addLocalMemory, addGlobalMemory } from "../api/client";

interface MemoryFormProps {
  mode: "local" | "global";
  userId: string;
  sessionId: string;
  defaultScope?: MemoryScope;
}

const MemoryForm: React.FC<MemoryFormProps> = ({
  mode,
  userId,
  sessionId
}) => {
  // Scope'u mode'a göre sabitliyoruz: local form -> "local", global form -> "global"
  const effectiveScope: MemoryScope =
    mode === "local" ? "local" : "global";

  const [text, setText] = useState("");
  const [meta, setMeta] = useState<string>("{}");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MemoryRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const title =
    mode === "local" ? "Add Local Memory" : "Add Global Memory";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    let metaObj: Record<string, unknown> | undefined;
    if (meta.trim()) {
      try {
        metaObj = JSON.parse(meta);
      } catch {
        setError("Meta alanı geçerli bir JSON olmalıdır.");
        return;
      }
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        scope: effectiveScope,       // <- burada her zaman "local" veya "global"
        user_id: userId,
        session_id: sessionId,
        text,
        meta: metaObj
      };

      const data =
        mode === "local"
          ? await addLocalMemory(payload)
          : await addGlobalMemory(payload);

      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError("Memory eklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="memory-panel">
      <h2>{title}</h2>

      <form className="memory-form" onSubmit={handleSubmit}>
        <div className="field-row">
          <div className="field">
            <label>Scope</label>
            <input
              value={effectiveScope}
              disabled
            />
          </div>
          <div className="field">
            <label>User ID</label>
            <input value={userId} disabled />
          </div>
          <div className="field">
            <label>Session ID</label>
            <input value={sessionId} disabled />
          </div>
        </div>

        <div className="field">
          <label>Text</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="Memory olarak kaydedilecek metin..."
          />
        </div>

        <div className="field">
          <label>Meta (JSON)</label>
          <textarea
            value={meta}
            onChange={(e) => setMeta(e.target.value)}
            rows={3}
            placeholder='{"source": "manual", "channel": "web"}'
          />
        </div>

        <button type="submit" disabled={loading || !text.trim()}>
          {loading ? "Kaydediliyor..." : "Memory Ekle"}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="memory-result">
          <div>
            <strong>ID:</strong> {result.id}
          </div>
          <div>
            <strong>Scope:</strong> {result.scope}
          </div>
          <div>
            <strong>Text:</strong> {result.text}
          </div>
          <div>
            <strong>Model:</strong> {result.model}
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryForm;
