import React from 'react';

export default function StatusStrip({ status, isStreaming, hasStartedTokens }) {
  if (!status || !isStreaming || hasStartedTokens) {
    return null;
  }

  const { stage, detail } = status;
  if (stage === 'synthesis' || stage === 'done') {
    return null;
  }

  return (
    <div className="my-1 flex items-center gap-2 font-mono text-xs theme-text-muted transition-all duration-300">
      <span className="h-2 w-2 rounded-full bg-[var(--palette-warm-sand)] animate-pulse shrink-0" />
      <span className="truncate">{detail || stage}</span>
    </div>
  );
}
