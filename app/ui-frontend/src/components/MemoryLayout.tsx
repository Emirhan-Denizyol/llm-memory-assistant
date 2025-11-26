// src/components/MemoryLayout.tsx

import React from "react";
import MemoryForm from "./MemoryForm";
import MemorySearch from "./MemorySearch";

interface MemoryLayoutProps {
  userId: string;
  sessionId: string;
  view: "local" | "global" | "search";
}

const MemoryLayout: React.FC<MemoryLayoutProps> = ({
  userId,
  sessionId,
  view
}) => {
  if (!userId || !sessionId) {
    return (
      <div className="memory-panel">
        <h2>Memory</h2>
        <p>
          Memory işlemleri için lütfen üstte User ID ve Session ID alanlarını
          doldurun.
        </p>
      </div>
    );
  }

  if (view === "local") {
    return (
      <MemoryForm mode="local" userId={userId} sessionId={sessionId} />
    );
  }

  if (view === "global") {
    return (
      <MemoryForm mode="global" userId={userId} sessionId={sessionId} />
    );
  }

  return (
    <MemorySearch userId={userId} sessionId={sessionId} />
  );
};

export default MemoryLayout;
