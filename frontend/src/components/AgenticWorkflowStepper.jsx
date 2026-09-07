import React, { useState, useEffect } from 'react';
import { Loader2, Download } from 'lucide-react';

const TOOL_LABELS = {
  ocr_vlm: 'Used OCR & Vision Inspection',
  code_sandbox: 'Used Python Code Sandbox',
  rag_kb: 'Searched RAG Knowledge Base',
  doc_gen: 'Used Document Generator',
  math_eval: 'Evaluated Math Solver',
  spreadsheet: 'Used Spreadsheet Engine',
  file_io: 'Accessed Workspace File I/O'
};

export default function AgenticWorkflowStepper({ 
  routeDecision, 
  planSteps = [],
  toolCalls = [], 
  status = null,
  isStreaming = false,
  hasStartedTokens = false,
  isThinkingMode = false,
  elapsedSeconds = 0,
  durationSeconds = null
}) {
  // Stay expanded while active streaming is processing; collapse once turn completes
  const [isExpanded, setIsExpanded] = useState(isStreaming);
  const [userToggled, setUserToggled] = useState(false);
  const [expandedTools, setExpandedTools] = useState({});

  useEffect(() => {
    if (!userToggled) {
      if (isStreaming) {
        setIsExpanded(true);
      } else {
        setIsExpanded(false);
      }
    }
  }, [isStreaming, userToggled]);

  const handleToggleExpand = () => {
    setUserToggled(true);
    setIsExpanded((prev) => !prev);
  };

  const toggleToolExpand = (idx) => {
    setExpandedTools((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const modelRole = routeDecision?.role || 'reasoning';
  const selectedModel = routeDecision?.selected_model || 'qwen3.5:4b-q4_K_M';
  const hasTools = toolCalls.length > 0;

  const displayDuration = (durationSeconds !== null && durationSeconds !== undefined)
    ? Number(durationSeconds).toFixed(1)
    : (elapsedSeconds ? elapsedSeconds : null);

  // Header text (Claude style)
  const headerText = isStreaming
    ? (isThinkingMode ? `Thinking for ${elapsedSeconds}s...` : `Processing for ${elapsedSeconds}s...`)
    : (displayDuration
        ? (isThinkingMode ? `Thought for ${displayDuration}s` : `Processed in ${displayDuration}s`)
        : (isThinkingMode ? `Thought` : `Processed`));


  // Model-generated plan text string
  const planString = planSteps.length > 0
    ? planSteps.join(' -> ')
    : (hasTools ? `Execute tools -> Analyze -> Output response` : `Direct response synthesis`);

  return (
    <div className="my-2 font-mono text-sm">
      {/* Plain Text Collapsible Button (No Chevron Arrows, No Bolding) */}
      <button
        type="button"
        onClick={handleToggleExpand}
        className="border-0 bg-transparent p-0 text-left theme-text-muted hover:theme-text-primary transition-colors cursor-pointer text-sm font-mono"
      >
        <span className="flex items-center gap-2">
          {isStreaming && <Loader2 className="h-3.5 w-3.5 animate-spin theme-text-muted" />}
          <span>{headerText}</span>
        </span>
      </button>

      {/* Expanded Real-Time Text List (No Numbers, No Cards, Plain Muted Font) */}
      {isExpanded && (
        <div className="mt-2.5 ml-1 space-y-2 border-l border-[var(--border-muted)] pl-3 text-sm theme-text-muted font-mono">
          <div>
            Prompt routed to '{modelRole}' model
          </div>

          <div>
            Loading {selectedModel} into memory...
          </div>

          {/* Plain Text Expandable Tool Calls */}
          {hasTools && toolCalls.map((tc, idx) => {
            const label = TOOL_LABELS[tc.tool_name] || `Used ${tc.tool_name}`;
            const isToolExpanded = !!expandedTools[idx];

            let filename = null;
            if (tc.raw_output) {
              const meta = tc.raw_output.metadata || {};
              const pathStr = meta.output_path || meta.path;
              if (pathStr && typeof pathStr === 'string' && /\.(docx|pptx|ppt|xlsx|csv|pdf|png|txt)$/i.test(pathStr)) {
                filename = pathStr.split('/').pop().split('\\').pop();
              }
            }

            return (
              <div key={idx} className="my-1">
                <button
                  type="button"
                  onClick={() => toggleToolExpand(idx)}
                  className="border-0 bg-transparent p-0 text-left theme-text-muted hover:theme-text-primary transition-colors cursor-pointer text-sm font-mono"
                >
                  <span>{label} {tc.isRunning && '(running...)'}</span>
                </button>

                {isToolExpanded && (
                  <div className="mt-1 ml-3 space-y-1 text-xs theme-text-muted border-l border-[var(--border-muted)] pl-2 font-mono">
                    {tc.output_summary && (
                      <div>{tc.output_summary}</div>
                    )}
                    {tc.tool_input && (
                      <div>
                        Parameters: {JSON.stringify(tc.tool_input)}
                      </div>
                    )}
                    {filename && (
                      <div className="pt-0.5">
                        <a
                          href={`http://localhost:8000/workspace/default_session/files/${filename}`}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 theme-text-muted underline hover:theme-text-primary transition-colors"
                        >
                          <Download className="h-3 w-3" />
                          <span>Download {filename}</span>
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {hasTools && (
            <div>
              Analyzing tool outputs...
            </div>
          )}

          {!isStreaming && (
            <div>
              Done
            </div>
          )}
        </div>
      )}
    </div>
  );
}
