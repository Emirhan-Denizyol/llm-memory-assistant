// src/components/MemorySearch.tsx

import React, { useState } from "react";
import type { MemoryScope, MemoryRecord } from "../api/types";
import { searchMemory } from "../api/client";

interface MemorySearchProps {
  userId: string;
  sessionId: string;
  defaultScope?: MemoryScope;
}

const MemorySearch: React.FC<MemorySearchProps> = ({
  userId,
  sessionId,
  defaultScope = "local"
}) => {
  // Scope'u güvenli değerlere sabitliyoruz
  const [scope, setScope] = useState<MemoryScope>(defaultScope);
  const [query, setQuery] = useState("");
  const [topk, setTopk] = useState(10);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<MemoryRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const payload = {
        user_id: userId,
        q: query,
        scope: scope,      // local, global veya null
        session_id: sessionId,
        topk
      };

      const data = await searchMemory(payload);
      setResults(data.items || []);
    } catch (err) {
      console.error(err);
      setError("Memory araması sırasında hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="memory-panel">
      <h2>Search Memory</h2>

      <form className="memory-form" onSubmit={handleSearch}>
        <div className="field-row">
          <div className="field">
            <label>Scope</label>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value as MemoryScope)}
            >
              <option value="local">local</option>
              <option value="global">global</option>
              <option value="">(her ikisi)</option>
            </select>
          </div>

          <div className="field">
            <label>User ID</label>
            <input value={userId} disabled />
          </div>

          <div className="field">
            <label>Session ID</label>
            <input value={sessionId} disabled />
          </div>

          <div className="field">
            <label>Top K</label>
            <input
              type="number"
              min={1}
              max={100}
              value={topk}
              onChange={(e) => setTopk(Number(e.target.value) || 10)}
            />
          </div>
        </div>

        <div className="field">
          <label>Sorgu</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="örn: kahve, şehir, rol, tercih..."
          />
        </div>

        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? "Aranıyor..." : "Ara"}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {results.length > 0 && (
        <div className="memory-search-results">
          <div className="memory-search-header">
            {results.length} sonuç bulundu
          </div>

          <ul>
            {results.map((r) => (
              <li key={r.id} className="memory-result-item">
                <div className="memory-result-meta">
                  <span>ID: {r.id}</span>
                  <span>Scope: {r.scope}</span>
                  {r.session_id && <span>Session: {r.session_id}</span>}
                </div>
                <div className="memory-result-text">{r.text}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default MemorySearch;
