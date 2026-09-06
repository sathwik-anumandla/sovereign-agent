import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Download } from 'lucide-react';

const TOOL_LABELS = {
  ocr_vlm: 'Used OCR & Vision Inspection',
  code_sandbox: 'Used Python Code Execution',
  rag_kb: 'Searched Knowledge Base',
  doc_gen: 'Used Document Generator',
  math_eval: 'Evaluated Math Solver',
  spreadsheet: 'Used Tabular Data Engine',
  file_io: 'Accessed Workspace File I/O'
};

export default function ToolCard({ toolCall }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { tool_name, status, tool_input, output_summary, raw_output, isRunning } = toolCall;

  const label = TOOL_LABELS[tool_name] || `Used ${tool_name}`;

  // Extract generated file deliverable if present
  let generatedFilename = null;
  if (raw_output) {
    const meta = raw_output.metadata || {};
    const dataVal = raw_output.data || {};
    const pathStr = meta.output_path || meta.path || dataVal.output_path || dataVal.path;
    if (pathStr && typeof pathStr === 'string' && /\.(docx|pptx|ppt|xlsx|csv|pdf|png|txt)$/i.test(pathStr)) {
      generatedFilename = pathStr.split('/').pop().split('\\').pop();
    }
  }
  if (!generatedFilename && output_summary && output_summary.includes("'")) {
    const match = output_summary.match(/'([^']+\.(?:docx|pptx|ppt|xlsx|csv|pdf|png|txt))'/i);
    if (match) generatedFilename = match[1];
  }

  return (
    <div className="my-1.5 text-xs">
      {/* Claude-style Minimal Clickable Text Header */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1.5 border-0 bg-transparent p-0 text-left theme-text-muted hover:theme-text-primary transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 theme-text-muted" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 theme-text-muted" />
          )}
          <span className="font-medium text-[12px]">{label}</span>
        </button>

        {generatedFilename && (
          <a
            href={`http://localhost:8000/workspace/default_session/files/${generatedFilename}`}
            download
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded bg-[var(--bg-card)] px-2 py-0.5 text-[10px] theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0"
            title={`Download ${generatedFilename}`}
          >
            <Download className="h-3 w-3" />
            <span>Download {generatedFilename}</span>
          </a>
        )}
      </div>

      {/* Simple Minimal Expanded Card */}
      {isExpanded && (
        <div className="mt-2 rounded-lg card-bg p-3 border-0 text-[11px] space-y-2">
          {output_summary && (
            <div className="theme-text-primary font-sans leading-relaxed">
              {output_summary}
            </div>
          )}
          {tool_input && (
            <div>
              <span className="theme-text-muted font-mono text-[10px]">Parameters:</span>
              <pre className="mt-1 overflow-x-auto rounded bg-[var(--bg-sidebar)] p-2 font-mono text-[11px] theme-text-secondary border-0 m-0">
                {JSON.stringify(tool_input, null, 2)}
              </pre>
            </div>
          )}
          {raw_output && (
            <div>
              <span className="theme-text-muted font-mono text-[10px]">Result Payload:</span>
              <pre className="mt-1 max-h-40 overflow-y-auto overflow-x-auto rounded bg-[var(--bg-sidebar)] p-2 font-mono text-[11px] theme-text-secondary border-0 m-0">
                {JSON.stringify(raw_output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
