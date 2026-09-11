import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { 
  Paperclip, 
  ArrowUp, 
  File, 
  X, 
  Sparkles, 
  Loader2,
  PanelLeft,
  Copy,
  Check,
  ShieldCheck,
  BookOpen,
  UploadCloud,
  Trash2,
  FileText,
  Database,
  Sun,
  Moon,
  ChevronDown,
  Download,
  Eye,
  Share2,
  SquarePen,
  User,
  Key,
  LogOut,
  Sliders,
  RotateCcw,
  Pencil,
  Volume2,
  VolumeX
} from 'lucide-react';
import ToolCard from './ToolCard';
import AgenticWorkflowStepper from './AgenticWorkflowStepper';
import StatusStrip from './StatusStrip';

function CopyResponseButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="flex items-center justify-center rounded-md p-1 theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
      title={copied ? "Copied" : "Copy response"}
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-400" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

function RegenerateResponseButton({ onRegenerate, isStreaming }) {
  return (
    <button
      type="button"
      onClick={onRegenerate}
      disabled={isStreaming}
      className="flex items-center gap-1 rounded-md p-1 px-1.5 theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer disabled:opacity-40"
      title="Regenerate response"
    >
      <RotateCcw className={`h-3.5 w-3.5 ${isStreaming ? 'animate-spin' : ''}`} />
      <span className="text-[11px] font-medium">Regenerate</span>
    </button>
  );
}

function sanitizeTextForSpeech(text) {
  if (!text || typeof text !== 'string') return '';

  // 1. Extract thinking trace if any
  if (text.includes('<think>')) {
    if (text.includes('</think>')) {
      text = text.split('</think>').slice(1).join('</think>').trim();
    } else {
      text = '';
    }
  }

  // 2. Remove multi-line code blocks
  text = text.replace(/```[\s\S]*?```/g, ' [code block omitted] ');

  // 3. Clean LaTeX math formulas
  // Fractions (support nested braces)
  let prev;
  do {
    prev = text;
    text = text.replace(/\\frac\s*\{((?:[^{}]|\{[^{}]*\})*)\}\s*\{((?:[^{}]|\{[^{}]*\})*)\}/g, '($1) over ($2)');
  } while (text !== prev);

  // Square roots
  do {
    prev = text;
    text = text.replace(/\\sqrt\[([^\]]+)\]\{((?:[^{}]|\{[^{}]*\})*)\}/g, '$1 root of $2');
    text = text.replace(/\\sqrt\{((?:[^{}]|\{[^{}]*\})*)\}/g, 'square root of $1');
  } while (text !== prev);

  // Math operators and symbols
  text = text
    .replace(/\\pm/g, ' plus or minus ')
    .replace(/\\mp/g, ' minus or plus ')
    .replace(/\\times/g, ' times ')
    .replace(/\\div/g, ' divided by ')
    .replace(/\\cdot/g, ' dot ')
    .replace(/\\leq|\\le/g, ' is less than or equal to ')
    .replace(/\\geq|\\ge/g, ' is greater than or equal to ')
    .replace(/\\neq|\\ne/g, ' is not equal to ')
    .replace(/\\approx/g, ' is approximately ')
    .replace(/\\infty/g, ' infinity ')
    .replace(/\\Delta/g, 'Delta')
    .replace(/\\delta/g, 'delta')
    .replace(/\\alpha/g, 'alpha')
    .replace(/\\beta/g, 'beta')
    .replace(/\\gamma/g, 'gamma')
    .replace(/\\theta/g, 'theta')
    .replace(/\\pi/g, 'pi')
    .replace(/\\sigma/g, 'sigma')
    .replace(/\\omega/g, 'omega')
    .replace(/\\mu/g, 'mu')
    .replace(/\\lambda/g, 'lambda')
    .replace(/\\left\(|\\right\)/g, '')
    .replace(/\\left\[|\\right\]/g, '')
    .replace(/\\left\\\{|\\right\\\}/g, '')
    .replace(/\\quad|\\qquad|\\;|\\,|\\!/g, ' ')
    .replace(/\\text\{([^{}]+)\}/g, '$1');

  // Exponents: x^{2} or x^2
  text = text.replace(/([a-zA-Z0-9_\)\.\}]+)\^\{([^{}]+)\}/g, '$1 to the power of $2');
  text = text.replace(/([a-zA-Z0-9_\)\.\}]+)\^([0-9a-zA-Z])/g, '$1 to the power of $2');

  // Subscripts: x_1 or x_{1}
  text = text.replace(/([a-zA-Z])_\{([^{}]+)\}/g, '$1 sub $2');
  text = text.replace(/([a-zA-Z])_([0-9a-zA-Z]+)/g, '$1 sub $2');

  // Remove math delimiters
  text = text.replace(/\$\$(.+?)\$\$/gs, ' $1 ');
  text = text.replace(/\$([^\$]+)\$/g, ' $1 ');

  // 4. Clean Markdown syntax
  text = text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '') // images
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // links -> text
    .replace(/`([^`]+)`/g, '$1') // inline code
    .replace(/^#+\s+/gm, '') // headings
    .replace(/^\s*\|?[\s\-:|]+\|?\s*$/gm, '') // table header separator lines e.g. |---|---|
    .replace(/(\*\*|__)(.*?)\1/g, '$2') // bold
    .replace(/(\*|_)(.*?)\1/g, '$2') // italic
    .replace(/~~(.*?)~~/g, '$2') // strikethrough
    .replace(/^>\s+/gm, '') // blockquotes
    .replace(/^[*-]\s+/gm, '') // bullet lists
    .replace(/^\d+\.\s+/gm, '') // numbered lists
    .replace(/^[-*_]{3,}\s*$/gm, '') // hr
    .replace(/\|/g, ', ') // table pipes
    .replace(/,{2,}/g, ',') // multiple commas
    .replace(/\s*,\s*,\s*/g, ', ') // clean stray commas
    .replace(/:\s*\./g, ':') // colon dot
    .replace(/:\s*,/g, ':') // colon comma
    .replace(/\.\s*\./g, '.') // double period
    .replace(/\n{2,}/g, '. ') // multiple newlines -> period
    .replace(/\n/g, ' ') // single newline -> space
    .replace(/\s{2,}/g, ' ') // collapse whitespace
    .replace(/\s+([.,!?:;])/g, '$1') // clean spaces before punctuation
    .trim();

  return text;
}

function SpeakResponseButton({ text, messageIndex, activeSpeakingIndex, setActiveSpeakingIndex }) {
  const isSpeaking = activeSpeakingIndex === messageIndex;

  const handleToggleSpeak = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setActiveSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = sanitizeTextForSpeech(text);
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Samantha') || v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Siri') || v.default)) || voices.find(v => v.lang.startsWith('en'));
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.onend = () => {
      setActiveSpeakingIndex((curr) => (curr === messageIndex ? null : curr));
    };
    utterance.onerror = (e) => {
      console.warn('Speech synthesis error:', e);
      setActiveSpeakingIndex((curr) => (curr === messageIndex ? null : curr));
    };

    setActiveSpeakingIndex(messageIndex);
    window.speechSynthesis.speak(utterance);
  };

  if (typeof window !== 'undefined' && !('speechSynthesis' in window)) {
    return null;
  }

  return (
    <button
      type="button"
      onClick={handleToggleSpeak}
      className={`flex items-center gap-1 rounded-md p-1 px-1.5 transition-colors border-0 cursor-pointer ${
        isSpeaking
          ? 'bg-amber-500/15 text-amber-500 hover:bg-amber-500/25 font-medium'
          : 'theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] bg-transparent'
      }`}
      title={isSpeaking ? "Stop reading aloud" : "Read aloud"}
    >
      {isSpeaking ? (
        <>
          <VolumeX className="h-3.5 w-3.5 text-amber-500 animate-pulse" />
          <span className="text-[11px] font-medium text-amber-500">Stop</span>
        </>
      ) : (
        <>
          <Volume2 className="h-3.5 w-3.5" />
          <span className="text-[11px] font-medium">Read aloud</span>
        </>
      )}
    </button>
  );
}

function extractGeneratedFiles(msg, messages = []) {
  if (!msg) return [];

  // Blacklist of system/source code files and configs that must NEVER be shown as deliverables
  const BLACKLIST_FILES = new Set([
    'server.py', 'graph.py', 'route.py', 'registry.py', 'db.py', 'tool_interface.py',
    'phase1_inference.py', 'config_loader.py', 'package.json', 'models_config.json',
    'requirements.txt', '.env', 'dockerfile', 'tsconfig.json'
  ]);

  // 1. Collect all uploaded file names from all messages in the conversation
  const uploadedFileNames = new Set();
  messages.forEach((m) => {
    if (m.attachedFiles && Array.isArray(m.attachedFiles)) {
      m.attachedFiles.forEach((f) => {
        const fn = f.filename || f.original_filename || f.name;
        if (fn) {
          uploadedFileNames.add(fn.split(/[/\\]/).pop().toLowerCase());
        }
      });
    }
  });

  // 2. Collect all input file paths passed to read/analysis tools in this turn
  const inputToolFiles = new Set();
  const toolCalls = msg.toolCalls || [];
  toolCalls.forEach((tc) => {
    const toolName = (tc.name || tc.tool_name || tc.tool || (tc.function && tc.function.name) || '').toLowerCase();
    const args = tc.args || tc.input || tc.tool_input || (tc.function && tc.function.arguments) || {};

    // Generation tools produce OUTPUT deliverables; their arguments must NEVER be blacklisted as inputs!
    if (toolName.includes('doc_gen')) return;
    if (toolName.includes('file_io') && (args.action === 'write' || args.mode === 'write' || args.action === 'create')) return;

    if (typeof args === 'object' && args !== null) {
      Object.values(args).forEach((val) => {
        if (typeof val === 'string') {
          const cleanVal = val.split(/[/\\]/).pop().split('?')[0].toLowerCase();
          if (cleanVal.includes('.')) {
            inputToolFiles.add(cleanVal);
          }
        }
      });
    }
  });

  const filesMap = new Map();

  const addFile = (filename, rawPath) => {
    if (!filename) return;
    const cleanName = filename.split(/[/\\]/).pop().split('?')[0];
    if (!cleanName) return;

    const lowerClean = cleanName.toLowerCase();

    // STRICT FILTER 1: Blacklisted system/source code files
    if (BLACKLIST_FILES.has(lowerClean)) {
      return;
    }

    // STRICT FILTER 2: Do NOT include uploaded files or tool input files!
    if (uploadedFileNames.has(lowerClean) || inputToolFiles.has(lowerClean)) {
      return;
    }

    // Allowed deliverable extensions ONLY (documents, slides, spreadsheets, PDFs, generated images, archives)
    const validExts = ['docx', 'pptx', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'csv', 'zip'];
    const ext = (cleanName.split('.').pop() || '').toLowerCase();
    if (validExts.includes(ext) && !filesMap.has(cleanName)) {
      filesMap.set(cleanName, { filename: cleanName, rawPath: rawPath || cleanName });
    }
  };

  // Explicit generated files linked to this message via backend message_id or SSE final event
  const explicitGenerated = msg.generatedFiles || (msg.role === 'assistant' ? msg.files : null);
  if (Array.isArray(explicitGenerated)) {
    explicitGenerated.forEach((f) => {
      const fn = f.filename || f.original_filename || f.name;
      if (!fn) return;
      const cleanName = fn.split(/[/\\]/).pop().split('?')[0];
      const lowerClean = cleanName.toLowerCase();
      if (!BLACKLIST_FILES.has(lowerClean) && !uploadedFileNames.has(lowerClean)) {
        const ext = (cleanName.split('.').pop() || '').toLowerCase();
        const validExts = ['docx', 'pptx', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'csv', 'zip'];
        if (validExts.includes(ext) && !filesMap.has(cleanName)) {
          filesMap.set(cleanName, {
            filename: cleanName,
            rawPath: f.storage_path || cleanName,
            file_id: f.file_id
          });
        }
      }
    });
  }

  // 3. Scan tool calls for EXPLICIT output generated files
  toolCalls.forEach((tc) => {
    const toolName = (tc.name || tc.tool_name || tc.tool || (tc.function && tc.function.name) || '').toLowerCase();
    const args = tc.args || tc.input || tc.tool_input || (tc.function && tc.function.arguments) || {};
    const res = tc.result || tc.output || tc.output_summary || tc.raw_output || {};

    // Generation tool 1: doc_gen
    if (toolName.includes('doc_gen')) {
      if (args.output_filename) addFile(args.output_filename, args.output_filename);
      if (args.filename) addFile(args.filename, args.filename);
      if (args.output_path) addFile(args.output_path, args.output_path);
      if (typeof res === 'object' && res !== null) {
        if (res.output_filepath) addFile(res.output_filepath, res.output_filepath);
        if (res.output_path) addFile(res.output_path, res.output_path);
        if (res.filepath) addFile(res.filepath, res.filepath);
      }
    }

    // Generation tool 2: file_io (write / create action)
    if (toolName.includes('file_io') && (args.action === 'write' || args.mode === 'write' || args.action === 'create')) {
      if (args.filepath) addFile(args.filepath, args.filepath);
      if (args.file_path) addFile(args.file_path, args.file_path);
    }

    // Explicit output file paths starting with workspace/ or data/uploads/ in tool results
    const resStr = typeof res === 'string' ? res : JSON.stringify(res);
    const matches = resStr.matchAll(/(?:workspace\/[^\s"')`]+\/|data\/uploads\/[^\s"')`]+\/)([a-zA-Z0-9_\-.]+\.(?:docx|pptx|xlsx|pdf|png|jpe?g|gif|webp|svg|csv|zip))/gi);
    for (const match of matches) {
      addFile(match[1], match[0]);
    }
  });

  // 4. Scan assistant message content text for explicit workspace paths or mentioned deliverables if doc_gen was run
  if (msg.content) {
    const linkMatches = msg.content.matchAll(/\[([^\]]+)\]\(((?:workspace\/|data\/uploads\/|\/workspace\/|\/data\/uploads\/)[^)]+)\)/g);
    for (const match of linkMatches) {
      addFile(match[1], match[2]);
    }
    const workspaceTextMatches = msg.content.matchAll(/(?:workspace\/[^\s"')`]+\/|data\/uploads\/[^\s"')`]+\/)([a-zA-Z0-9_\-.]+\.(?:docx|pptx|xlsx|pdf|png|jpe?g|gif|webp|svg|csv|zip))/gi);
    for (const match of workspaceTextMatches) {
      addFile(match[1], match[0]);
    }

    // If doc_gen was executed in this turn, also capture the generated document name mentioned in text
    const hasDocGen = toolCalls.some((tc) => {
      const tn = (tc.name || tc.tool_name || tc.tool || (tc.function && tc.function.name) || '').toLowerCase();
      return tn.includes('doc_gen');
    });
    if (hasDocGen) {
      const docMatches = msg.content.matchAll(/\b([a-zA-Z0-9_\-.]+\.(?:docx|pptx|xlsx|pdf))\b/gi);
      for (const match of docMatches) {
        addFile(match[1], match[1]);
      }
    }
  }

  return Array.from(filesMap.values());
}

function DeliverableCard({ file, threadId, token, onPreview }) {
  const filename = file.filename;
  const ext = (filename.split('.').pop() || '').toLowerCase();
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext);
  
  const downloadUrl = `http://localhost:8000/workspace/${threadId}/files/${encodeURIComponent(filename)}?download=true${token ? `&token=${token}` : ''}`;
  const inlineUrl = `http://localhost:8000/workspace/${threadId}/files/${encodeURIComponent(filename)}${token ? `?token=${token}` : ''}`;

  return (
    <div className="flex items-center justify-between rounded-xl border border-[var(--bg-hover)]/40 bg-[var(--bg-card)] p-3 my-2 shadow-xs transition-all hover:border-[var(--bg-hover)]">
      <div className="flex items-center gap-3 truncate pr-2">
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg shrink-0 ${
          ext === 'docx' ? 'bg-blue-500/15 text-blue-400' :
          ext === 'pptx' ? 'bg-amber-500/15 text-amber-400' :
          ext === 'xlsx' ? 'bg-emerald-500/15 text-emerald-400' :
          ext === 'pdf' ? 'bg-red-500/15 text-red-400' :
          isImage ? 'bg-purple-500/15 text-purple-400' :
          'bg-slate-500/15 theme-text-secondary'
        }`}>
          <FileText className="h-4 w-4" />
        </div>
        <div className="truncate">
          <div className="font-semibold text-xs theme-text-primary truncate">{filename}</div>
          <div className="text-[10px] theme-text-muted font-mono uppercase mt-0.5">{ext} Deliverable</div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {isImage && onPreview && (
          <button
            type="button"
            onClick={() => onPreview({ filename, url: inlineUrl })}
            className="flex items-center gap-1 rounded-lg border-0 bg-[var(--bg-input)] px-2.5 py-1.5 text-xs font-medium theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
            title={`Preview ${filename}`}
          >
            <Eye className="h-3.5 w-3.5 text-blue-400" />
            <span>Preview</span>
          </button>
        )}
        <a
          href={downloadUrl}
          download={filename}
          className="flex items-center gap-1.5 rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-3 py-1.5 text-xs font-semibold hover:opacity-90 transition-all no-underline"
          title={`Download ${filename}`}
        >
          <Download className="h-3.5 w-3.5" />
          <span>Download</span>
        </a>
      </div>
    </div>
  );
}

function CodeBlock({ inline, className, children, ...props }) {
  const [copied, setCopied] = useState(false);
  const codeString = String(children).replace(/\n$/, '');
  const isInline = inline || (!className && !codeString.includes('\n'));

  if (isInline) {
    return (
      <code className="bg-[var(--bg-input)] text-[var(--text-accent)] font-mono text-sm px-1.5 py-0.5 rounded border-0 font-medium inline" {...props}>
        {children}
      </code>
    );
  }

  const match = /language-(\w+)/.exec(className || '');

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl border-0 bg-[var(--bg-sidebar)] overflow-hidden font-mono text-sm">
      <div className="flex items-center justify-between bg-[var(--bg-card)] px-3.5 py-2 border-0 text-xs theme-text-muted">
        <span className="font-medium lowercase tracking-wide theme-text-secondary">{match ? match[1] : 'code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center justify-center rounded p-1 theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors text-xs border-0 bg-transparent cursor-pointer"
          title={copied ? "Copied" : "Copy code"}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
      <div className="p-4 overflow-x-auto">
        <pre className="font-mono text-sm leading-relaxed text-[var(--text-primary)] bg-transparent border-0 m-0 p-0">
          <code {...props}>{children}</code>
        </pre>
      </div>
    </div>
  );
}

function FilePreviewModal({ file, onClose }) {
  const filename = file?.filename || 'Image Preview';
  const url = file?.url;
  const ext = (filename.split('.').pop() || '').toLowerCase();
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!file || !isImage) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150" onClick={onClose}>
      <div className="flex h-[85vh] w-full max-w-4xl flex-col rounded-2xl card-bg border-0 overflow-hidden theme-text-primary" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between border-0 px-5 py-3.5 bg-[var(--bg-card)]">
          <div className="flex items-center gap-2.5 truncate pr-4">
            <File className="h-4 w-4 theme-text-secondary shrink-0" />
            <span className="font-semibold text-sm theme-text-primary truncate">{filename}</span>
            <span className="rounded bg-[var(--bg-input)] px-2 py-0.5 text-[10px] font-mono uppercase theme-text-muted">
              {ext}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {url && (
              <a
                href={url}
                download={filename}
                className="flex items-center gap-1.5 rounded-lg bg-[var(--bg-input)] px-3 py-1.5 text-xs font-medium theme-text-primary hover:bg-[var(--bg-hover)] transition-colors no-underline"
                title="Download image"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download</span>
              </a>
            )}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
              title="Close Preview (Esc)"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Viewer */}
        <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-[var(--bg-sidebar)]">
          {url && (
            <img src={url} alt={filename} className="max-h-full max-w-full object-contain rounded-lg border-0" />
          )}
        </div>
      </div>
    </div>
  );
}

function preprocessMarkdownMath(content) {
  if (!content || typeof content !== 'string') return '';
  let processed = content;

  // 1. Convert \[ ... \] display LaTeX to $$\n...\n$$
  processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => {
    return `$$\n${math.trim()}\n$$`;
  });

  // 2. Convert \( ... \) inline LaTeX to $...$
  processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => {
    return `$${math.trim()}$`;
  });

  // 3. Escape isolated currency amounts like $100, $2,500.50 so they don't break math parsing
  processed = processed.replace(/(^|\s)\$(\d[\d,]*(?:\.\d+)?)(?=\s|$|[.,;!?](?:\s|$))/g, '$1\\$$$2');

  // 4. Convert standalone single-line $$...$$ on its own line to multi-line $$\n...\n$$ for display math
  processed = processed.replace(/^(\s*)\$\$(.+?)\$\$(\s*)$/gm, (_, p1, p2, p3) => {
    return `${p1}$$\n${p2.trim()}\n$$${p3}`;
  });

  return processed;
}

function extractThinkingAndAnswer(content) {
  if (!content || typeof content !== 'string') return { thinking: '', answer: '' };
  if (content.includes('<think>')) {
    if (content.includes('</think>')) {
      const parts = content.split('</think>');
      const think = parts[0].replace('<think>', '').trim();
      const answer = parts.slice(1).join('</think>').trim();
      return { thinking: think, answer };
    } else {
      const think = content.replace('<think>', '').trim();
      return { thinking: think, answer: '' };
    }
  }
  return { thinking: '', answer: content };
}

function ThoughtBlock({ thinking, isStreaming }) {
  const [isOpen, setIsOpen] = useState(false);
  if (!thinking) return null;

  return (
    <div className="my-2.5 rounded-xl border border-[var(--bg-hover)]/60 bg-[var(--bg-card)]/60 p-2.5 text-xs shadow-xs">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 border-0 bg-transparent p-0 theme-text-muted hover:theme-text-primary cursor-pointer font-medium text-xs"
      >
        <Sparkles className="h-3.5 w-3.5 text-amber-500/80" />
        <span>{isStreaming ? 'Thinking through problem...' : (isOpen ? 'Hide Thought Process' : 'Show Thought Process')}</span>
        <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {(isOpen || isStreaming) && (
        <div className="mt-2 pt-2 border-t border-[var(--bg-hover)]/40 theme-text-secondary whitespace-pre-wrap leading-relaxed font-sans text-xs max-h-96 overflow-y-auto">
          {thinking}
        </div>
      )}
    </div>
  );
}

const markdownComponents = {
  h1: ({ children }) => <h1 className="text-xl font-bold theme-text-primary mt-4 mb-2 border-0 pb-1">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-bold theme-text-primary mt-3 mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-semibold theme-text-primary mt-2 mb-1">{children}</h3>,
  p: ({ children }) => <p className="mb-2 leading-relaxed theme-text-primary font-sans text-base">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1 text-base theme-text-primary">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1 text-base theme-text-primary">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  blockquote: ({ children }) => <blockquote className="border-0 pl-3 my-2 theme-text-muted italic text-base">{children}</blockquote>,
  code: CodeBlock,
  table: ({ children }) => <div className="my-3 overflow-x-auto rounded-xl border-0"><table className="w-full border-collapse text-sm text-left">{children}</table></div>,
  th: ({ children }) => <th className="border-0 bg-[var(--bg-input)] px-3.5 py-2.5 font-semibold theme-text-primary">{children}</th>,
  td: ({ children }) => <td className="border-0 px-3.5 py-2.5 theme-text-primary bg-[var(--bg-card)]/40">{children}</td>,
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-[var(--palette-warm-sand)] underline hover:opacity-80 font-medium">{children}</a>,
  hr: () => <hr className="my-4 border-0" />
};

export default function ChatWindow({
  activeThreadId,
  activeThreadTitle,
  messages,
  toolCallsMap,
  isStreaming,
  connectionError,
  routeDecision,
  onSendMessage,
  onFileUpload,
  onNewThread,
  isSidebarOpen,
  onToggleSidebar,
  isThinkingMode = false,
  onToggleThinking,
  theme = 'light',
  onToggleTheme,
  showKbModal = false,
  onCloseKbModal,
  token,
  modelConfig,
  currentUser,
  onLogout,
  onOpenAdminModal,
  onOpen2faModal
}) {
  const [showAirGapModal, setShowAirGapModal] = useState(false);
  const [netTelemetry, setNetTelemetry] = useState(null);
  const [selectedModelMode, setSelectedModelMode] = useState('auto');
  const [showModelMenu, setShowModelMenu] = useState(false);
  const modelMenuRef = useRef(null);

  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const profileMenuRef = useRef(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdStatus, setPwdStatus] = useState(null);
  const [isChangingPwd, setIsChangingPwd] = useState(false);

  const [inputText, setInputText] = useState('');
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [previewFile, setPreviewFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const [editingMsgIdx, setEditingMsgIdx] = useState(null);
  const [editInputText, setEditInputText] = useState('');

  const handleSaveEditPrompt = (idx) => {
    if (isStreaming || !editInputText.trim()) return;
    const targetMsg = messages[idx];
    const fileIds = (targetMsg?.attachedFiles || []).map((f) => f.file_id || f.id).filter(Boolean);
    const attachedFiles = targetMsg?.attachedFiles || [];
    const text = editInputText.trim();
    setEditingMsgIdx(null);
    onSendMessage(text, fileIds, attachedFiles, selectedModelMode, idx);
  };

  const handleRegenerateResponse = (assistantIdx) => {
    if (isStreaming) return;
    let userIdx = -1;
    for (let i = assistantIdx - 1; i >= 0; i--) {
      if (messages[i] && messages[i].role === 'user') {
        userIdx = i;
        break;
      }
    }

    if (userIdx === -1) return;

    const userMsg = messages[userIdx];
    const fileIds = (userMsg.attachedFiles || []).map((f) => f.file_id || f.id).filter(Boolean);
    const attachedFiles = userMsg.attachedFiles || [];
    const text = userMsg.content || '';

    onSendMessage(text, fileIds, attachedFiles, selectedModelMode, userIdx);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (modelMenuRef.current && !modelMenuRef.current.contains(event.target)) {
        setShowModelMenu(false);
      }
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleChangePasswordSubmit = async (e) => {
    e.preventDefault();
    if (!oldPassword || !newPassword || isChangingPwd) return;

    if (newPassword !== confirmPassword) {
      setPwdStatus({ type: 'error', message: 'New passwords do not match.' });
      return;
    }

    if (newPassword.length < 6) {
      setPwdStatus({ type: 'error', message: 'Password must be at least 6 characters long.' });
      return;
    }

    setIsChangingPwd(true);
    setPwdStatus(null);

    try {
      const res = await fetch('http://localhost:8000/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to change password');
      }

      setPwdStatus({ type: 'success', message: 'Password updated successfully!' });
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => {
        setShowPasswordModal(false);
        setPwdStatus(null);
      }, 1500);
    } catch (err) {
      setPwdStatus({ type: 'error', message: err.message });
    } finally {
      setIsChangingPwd(false);
    }
  };

  const fetchNetTelemetry = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/network/status', {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        setNetTelemetry(data);
      }
    } catch (err) {
      console.error('Error fetching network telemetry:', err);
    }
  };

  useEffect(() => {
    if (showAirGapModal) {
      fetchNetTelemetry();
    }
  }, [showAirGapModal]);

  // Knowledge Base State
  const [kbData, setKbData] = useState({ files: [], total_documents: 0, total_chunks: 0 });
  const [isIngestingKb, setIsIngestingKb] = useState(false);
  const kbFileInputRef = useRef(null);

  const fetchKbFiles = async () => {
    if (!token) return;
    try {
      const res = await fetch('http://localhost:8000/knowledge_base/files', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          const totalChunks = data.reduce((acc, f) => acc + (f.chunk_count || 0), 0);
          setKbData({ files: data, total_documents: data.length, total_chunks: totalChunks });
        } else {
          setKbData({
            files: data.files || [],
            total_documents: data.total_documents ?? (data.files ? data.files.length : 0),
            total_chunks: data.total_chunks || 0
          });
        }
      }
    } catch (err) {
      console.error('Error fetching KB files:', err);
    }
  };

  useEffect(() => {
    if (showKbModal && token) {
      fetchKbFiles();
    }
  }, [showKbModal, token]);

  const handleKbFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0 || !token) return;

    setIsIngestingKb(true);
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        await fetch('http://localhost:8000/knowledge_base/upload', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });
      } catch (err) {
        console.error('Error uploading KB file:', err);
      }
    }
    await fetchKbFiles();
    setIsIngestingKb(false);
    if (kbFileInputRef.current) kbFileInputRef.current.value = '';
  };

  const handleDeleteKbFile = async (filename) => {
    if (!token) return;
    try {
      await fetch(`http://localhost:8000/knowledge_base/files/${filename}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      await fetchKbFiles();
    } catch (err) {
      console.error('Error deleting KB file:', err);
    }
  };

  // Live stopwatch timer state for Claude-style response timer
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [lastTurnDuration, setLastTurnDuration] = useState(null);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  // Manage stopwatch counter during active streaming
  useEffect(() => {
    if (isStreaming) {
      startTimeRef.current = Date.now();
      setElapsedSeconds(0);
      setLastTurnDuration(null);
      timerRef.current = setInterval(() => {
        if (startTimeRef.current) {
          const diff = Math.floor((Date.now() - startTimeRef.current) / 1000);
          setElapsedSeconds(diff);
        }
      }, 500);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (startTimeRef.current) {
        const finalDiff = Math.max(1, Math.floor((Date.now() - startTimeRef.current) / 1000));
        setLastTurnDuration(finalDiff);
        startTimeRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isStreaming]);

  // Active text-to-speech reading state
  const [activeSpeakingIndex, setActiveSpeakingIndex] = useState(null);

  // Clean up active speech when switching threads or unmounting ChatWindow
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [activeThreadId]);

  // Cancel ongoing speech when a new response starts streaming
  useEffect(() => {
    if (isStreaming && typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setActiveSpeakingIndex(null);
    }
  }, [isStreaming]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, toolCallsMap, isStreaming, elapsedSeconds]);

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0 || !activeThreadId) return;

    setIsUploading(true);
    for (const file of files) {
      try {
        const uploaded = await onFileUpload(file);
        if (uploaded) {
          setAttachedFiles((prev) => [...prev, uploaded]);
        }
      } catch (err) {
        console.error('File upload failed:', err);
      }
    }
    setIsUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachedFile = (file_id) => {
    setAttachedFiles((prev) => prev.filter((f) => f.file_id !== file_id));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((!inputText.trim() && attachedFiles.length === 0) || isStreaming) return;

    const fileIds = attachedFiles.map((f) => f.file_id);
    onSendMessage(inputText, fileIds, attachedFiles, selectedModelMode);
    setInputText('');
    setAttachedFiles([]);
  };

  const canSubmit = (inputText.trim() || attachedFiles.length > 0) && !isStreaming;

  return (
    <div className="flex h-full flex-1 flex-col app-bg theme-text-primary">
      {/* Top Header Bar */}
      <header className="flex h-14 items-center justify-between border-0 header-bg px-4 z-20 relative">
        <div className="flex items-center gap-2">
          {!isSidebarOpen && (
            <button
              onClick={onToggleSidebar}
              className="flex h-8 w-8 items-center justify-center rounded-lg theme-text-muted hover:bg-[var(--bg-hover)] hover:theme-text-primary transition-colors border-0 bg-transparent cursor-pointer"
              title="Open sidebar"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
          )}

          {onNewThread && (
            <button
              type="button"
              onClick={onNewThread}
              className="flex h-8 w-8 items-center justify-center rounded-lg theme-text-muted hover:bg-[var(--bg-hover)] hover:theme-text-primary transition-colors border-0 bg-transparent cursor-pointer"
              title="New Chat"
            >
              <SquarePen className="h-4 w-4" />
            </button>
          )}

          <div className="flex items-center gap-2 truncate ml-1">
            <span className="text-sm font-semibold theme-text-primary truncate max-w-xs sm:max-w-md">
              {activeThreadTitle || 'Sovereign Agent'}
            </span>
          </div>
        </div>

        {/* Right Header Actions: Air-Gap Badge and Top-Right User Profile Avatar */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowAirGapModal(true)}
            className="hidden sm:flex items-center gap-2 rounded-full border-0 bg-[var(--bg-card)] px-3 py-1 text-xs theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary transition-colors cursor-pointer"
            title="Click to view Sovereign Air-Gap Network Audit Telemetry"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--text-primary)]" />
            <span className="font-mono text-[11px] font-medium">Air-Gapped</span>
          </button>

          {/* User Profile Avatar in Top-Right Corner */}
          <div className="relative" ref={profileMenuRef}>
            <button
              type="button"
              onClick={() => setShowProfileMenu((prev) => !prev)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-bold text-xs shadow-xs hover:opacity-90 transition-all border-0 cursor-pointer"
              title={currentUser?.name || 'User Profile'}
            >
              {(currentUser?.name || currentUser?.username || 'A')[0].toUpperCase()}
            </button>

            {/* Top-Right Profile Dropdown Popover Menu */}
            {showProfileMenu && (
              <div className="absolute right-0 top-full mt-2 w-56 z-50 rounded-2xl card-bg p-2 shadow-lg border-0 space-y-1 animate-in fade-in zoom-in-95 duration-100 theme-text-primary">
                <div className="px-3 py-2 border-b border-[var(--bg-hover)]/30">
                  <div className="font-bold text-xs theme-text-primary truncate">
                    {currentUser?.name || 'Authenticated User'}
                  </div>
                  <div className="text-[10px] theme-text-muted font-mono truncate mt-0.5">
                    @{currentUser?.username || 'user'} · {currentUser?.department || 'Operations'}
                  </div>
                  <div className="mt-1.5 inline-block rounded-md bg-[var(--bg-input)] px-2 py-0.5 text-[9px] font-bold uppercase font-mono theme-text-muted">
                    {currentUser?.role || 'USER'}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setShowProfileMenu(false);
                    setShowPasswordModal(true);
                  }}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
                >
                  <Key className="h-3.5 w-3.5 theme-text-secondary" />
                  <span>Change Password</span>
                </button>

                {onOpen2faModal && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowProfileMenu(false);
                      onOpen2faModal();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
                  >
                    <ShieldCheck className="h-3.5 w-3.5 theme-text-secondary" />
                    <span>2FA Security</span>
                  </button>
                )}

                {currentUser?.role === 'admin' && onOpenAdminModal && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowProfileMenu(false);
                      onOpenAdminModal();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
                  >
                    <Sliders className="h-3.5 w-3.5 theme-text-secondary" />
                    <span>Admin Dashboard</span>
                  </button>
                )}

                {onLogout && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowProfileMenu(false);
                      onLogout();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs text-red-500 hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer pt-1.5"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Logout</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {!activeThreadId ? (
        <div className="flex h-full flex-1 flex-col items-center justify-center p-6 text-center theme-text-primary">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] border-0">
            <Sparkles className="h-7 w-7" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight theme-text-primary">
            Sovereign Agent AI
          </h2>
          <p className="mt-2 text-sm theme-text-muted max-w-md">
            Air-gapped industrial assistant powered by open-weight LLMs. Select a chat or create a new conversation to start.
          </p>
        </div>
      ) : (
        <>
          {/* Messages Stream Container (Claude AI Centered Layout) */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && !isStreaming && (
            <div className="py-10 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] border-0">
                <Sparkles className="h-6 w-6" />
              </div>
              <h2 className="text-xl font-bold tracking-tight theme-text-primary">
                How can Sovereign Agent help you today?
              </h2>
              <p className="mt-1 text-xs theme-text-muted max-w-md mx-auto">
                Air-gapped industrial assistant with 3-stage waterfall router and 7 standalone tools.
              </p>

              <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
                <button
                  type="button"
                  onClick={() => onSendMessage("Extract all findings from ignore-files/ocr-test/test-1.pdf, query our RAG knowledge base for approval thresholds, and generate a formal Word document approval note deliverable.", [], [])}
                  className="rounded-xl border-0 card-bg p-4 hover:bg-[var(--bg-hover)] transition-all group text-left cursor-pointer"
                >
                  <div className="flex items-center gap-1.5 text-xs font-semibold theme-text-primary group-hover:theme-text-accent">
                    <FileText className="h-4 w-4 text-emerald-400" />
                    <span>Scanned PDF → Word Deliverable</span>
                  </div>
                  <div className="mt-1 text-[11px] theme-text-muted leading-relaxed">
                    Runs OCR on scanned PDF report, queries procurement thresholds in RAG KB, and drafts Word (.docx) approval note.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => onSendMessage("Analyze sensor_logs.csv for thermal anomalies exceeding 150°C using Python code_sandbox, and generate a formatted Excel deliverable with anomaly statistics.", [], [])}
                  className="rounded-xl border-0 card-bg p-4 hover:bg-[var(--bg-hover)] transition-all group text-left cursor-pointer"
                >
                  <div className="flex items-center gap-1.5 text-xs font-semibold theme-text-primary group-hover:theme-text-accent">
                    <Database className="h-4 w-4 text-blue-400" />
                    <span>CSV Analysis → Excel Deliverable</span>
                  </div>
                  <div className="mt-1 text-[11px] theme-text-muted leading-relaxed">
                    Executes Python code sandbox to analyze CSV telemetry data and generates a structured Excel (.xlsx) report.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => onSendMessage("Generate a 3-slide executive PowerPoint presentation deliverable (.pptx) summarizing the inspection findings and action items for the CDU-2 refinery unit.", [], [])}
                  className="rounded-xl border-0 card-bg p-4 hover:bg-[var(--bg-hover)] transition-all group text-left cursor-pointer"
                >
                  <div className="flex items-center gap-1.5 text-xs font-semibold theme-text-primary group-hover:theme-text-accent">
                    <BookOpen className="h-4 w-4 text-amber-400" />
                    <span>Executive PowerPoint Slides</span>
                  </div>
                  <div className="mt-1 text-[11px] theme-text-muted leading-relaxed">
                    Composes a multi-slide executive PowerPoint (.pptx) presentation deliverable summarizing technical inspection findings.
                  </div>
                </button>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            const isLastAssistant = !isUser && idx === messages.length - 1;

            return (
              <div key={idx} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                {/* User Message: Claude-style Right-Aligned Capsule (Borderless) */}
                {isUser ? (
                  <div className="ml-auto max-w-[85%] space-y-2">
                    {/* Attached File Chips */}
                    {msg.attachedFiles && msg.attachedFiles.length > 0 && (
                      <div className="flex flex-wrap justify-end gap-2">
                        {msg.attachedFiles.map((file, fIdx) => {
                          const fname = file.filename || file.original_filename || file.name || 'Attached File';
                          const isImg = /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(fname);
                          const fileUrl = activeThreadId ? `http://localhost:8000/workspace/${activeThreadId}/files/${encodeURIComponent(fname)}${token ? `?token=${token}` : ''}` : null;
                          const downloadUrl = activeThreadId ? `http://localhost:8000/workspace/${activeThreadId}/files/${encodeURIComponent(fname)}?download=true${token ? `&token=${token}` : ''}` : null;

                          return (
                            <div key={fIdx} className="flex flex-col items-end gap-1 max-w-[240px]">
                              {isImg && fileUrl && (
                                <button
                                  type="button"
                                  onClick={() => setPreviewFile({ filename: fname, url: fileUrl })}
                                  className="block overflow-hidden rounded-xl border-0 hover:opacity-90 transition-opacity bg-transparent cursor-pointer p-0 text-left"
                                  title={`Preview ${fname}`}
                                >
                                  <img
                                    src={fileUrl}
                                    alt={fname}
                                    className="max-h-[140px] w-auto max-w-full object-cover rounded-xl"
                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                  />
                                </button>
                              )}
                              {fileUrl ? (
                                isImg ? (
                                  <button
                                    type="button"
                                    onClick={() => setPreviewFile({ filename: fname, url: fileUrl })}
                                    className="flex items-center gap-1.5 rounded-lg border-0 card-bg px-2.5 py-1 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer text-left"
                                    title={`Preview ${fname}`}
                                  >
                                    <Eye className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                                    <span className="truncate max-w-[180px]">{fname}</span>
                                  </button>
                                ) : (
                                  <a
                                    href={downloadUrl}
                                    download={fname}
                                    className="flex items-center gap-1.5 rounded-lg border-0 card-bg px-2.5 py-1 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer text-left no-underline"
                                    title={`Download ${fname}`}
                                  >
                                    <Download className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                                    <span className="truncate max-w-[180px]">{fname}</span>
                                  </a>
                                )
                              ) : (
                                <div className="flex items-center gap-1.5 rounded-lg border-0 card-bg px-2.5 py-1 text-xs theme-text-primary">
                                  <File className="h-3.5 w-3.5 theme-text-muted shrink-0" />
                                  <span className="truncate max-w-[180px]">{fname}</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                    {editingMsgIdx === idx ? (
                      <div className="ml-auto w-full max-w-[85%] space-y-2 card-bg rounded-2xl p-3.5 border-0 shadow-sm">
                        <div className="text-xs font-semibold theme-text-secondary mb-1">Edit Prompt</div>
                        <textarea
                          value={editInputText}
                          onChange={(e) => setEditInputText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              handleSaveEditPrompt(idx);
                            }
                          }}
                          rows={2}
                          className="w-full resize-none border-0 bg-[var(--bg-input)] p-2.5 text-xs theme-text-primary rounded-xl focus:outline-none leading-relaxed font-sans"
                        />
                        <div className="flex items-center justify-end gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => setEditingMsgIdx(null)}
                            className="rounded-lg px-3 py-1 text-xs theme-text-muted hover:bg-[var(--bg-hover)] border-0 cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveEditPrompt(idx)}
                            disabled={!editInputText.trim() || isStreaming}
                            className="rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-3.5 py-1 text-xs font-semibold hover:opacity-90 transition-all border-0 cursor-pointer disabled:opacity-50"
                          >
                            Save & Submit
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="relative group/userchip flex flex-col items-end">
                        <div className="rounded-2xl bg-[var(--bg-user-chip)] border-0 px-4 py-3 text-sm text-[var(--text-user-chip)] leading-relaxed font-sans">
                          {msg.content}
                        </div>
                        {!isStreaming && (
                          <div className="pt-1 flex items-center justify-end opacity-80 hover:opacity-100 transition-opacity">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingMsgIdx(idx);
                                setEditInputText(msg.content || '');
                              }}
                              className="flex items-center gap-1 rounded-md p-1 px-1.5 text-xs theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
                              title="Edit prompt"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                              <span className="text-[11px]">Edit</span>
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Assistant Message: Agentic Workflow Stepper, Ephemeral Ambient Status Strip & Deliverable Output */
                  <div className="mr-auto w-full space-y-2 pt-1">
                    {/* Ephemeral Ambient Status Strip */}
                    <StatusStrip
                      status={msg.status}
                      isStreaming={isStreaming && isLastAssistant}
                      hasStartedTokens={msg.hasStartedTokens}
                    />

                    {/* Top Agentic Workflow Stepper Timeline */}
                    <AgenticWorkflowStepper
                      activeThreadId={activeThreadId}
                      routeDecision={msg.routeDecision || routeDecision}
                      planSteps={msg.planSteps || []}
                      toolCalls={msg.toolCalls || []}
                      isStreaming={isStreaming && isLastAssistant}
                      hasStartedTokens={msg.hasStartedTokens || (!isStreaming && !!msg.content)}
                      isThinkingMode={isThinkingMode}
                      elapsedSeconds={elapsedSeconds}
                      durationSeconds={msg.durationSeconds}
                    />

                    {/* Final Response Markdown Text Content */}
                    {msg.content && (
                      <div className="markdown-body font-sans text-sm theme-text-primary pt-1 pl-1">
                        {(() => {
                          const { thinking: thinkingTrace, answer: mainAnswer } = extractThinkingAndAnswer(msg.content);
                          return (
                            <>
                              {thinkingTrace && (
                                <ThoughtBlock
                                  thinking={thinkingTrace}
                                  isStreaming={isStreaming && isLastAssistant && !mainAnswer}
                                />
                              )}
                              {mainAnswer && (
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: true }]]}
                                  rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
                                  components={markdownComponents}
                                >
                                  {preprocessMarkdownMath(mainAnswer)}
                                </ReactMarkdown>
                              )}
                            </>
                          );
                        })()}
                        {(!isStreaming || !isLastAssistant) && (
                          <div className="pt-1.5 flex items-center gap-2 text-xs theme-text-muted">
                            <CopyResponseButton text={extractThinkingAndAnswer(msg.content).answer || msg.content} />
                            <SpeakResponseButton
                              text={extractThinkingAndAnswer(msg.content).answer || msg.content}
                              messageIndex={idx}
                              activeSpeakingIndex={activeSpeakingIndex}
                              setActiveSpeakingIndex={setActiveSpeakingIndex}
                            />
                            <RegenerateResponseButton
                              onRegenerate={() => handleRegenerateResponse(idx)}
                              isStreaming={isStreaming}
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Generated Deliverables Section */}
                    {(() => {
                      const deliverables = extractGeneratedFiles(msg, messages);
                      if (deliverables.length === 0) return null;
                      return (
                        <div className="pt-2 space-y-2">
                          <div className="text-xs font-semibold theme-text-muted font-mono uppercase tracking-wider pl-1">
                            Generated Deliverables
                          </div>
                          {deliverables.map((del, dIdx) => (
                            <DeliverableCard
                              key={dIdx}
                              file={del}
                              threadId={activeThreadId}
                              token={token}
                              onPreview={setPreviewFile}
                            />
                          ))}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            );
          })}

          {/* Active Streaming Placeholder (before first assistant token arrives or during initial tool execution) */}
          {isStreaming && (messages.length === 0 || messages[messages.length - 1].role === 'user') && (
            <div className="mr-auto w-full space-y-2 pt-1">
              <StatusStrip
                status={messages[messages.length - 1]?.status}
                isStreaming={true}
                hasStartedTokens={false}
              />
              <AgenticWorkflowStepper
                activeThreadId={activeThreadId}
                routeDecision={routeDecision}
                planSteps={[]}
                toolCalls={toolCallsMap || []}
                isStreaming={true}
                hasStartedTokens={false}
                isThinkingMode={isThinkingMode}
                elapsedSeconds={elapsedSeconds}
                durationSeconds={null}
              />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Connection Error Banner */}
      {connectionError && (
        <div className="mx-auto mb-2 flex max-w-3xl items-center gap-2 rounded-lg border-0 bg-[var(--bg-card)] p-2.5 px-4 text-xs theme-text-muted">
          <span>{connectionError}</span>
        </div>
      )}

      {/* Compact Floating Centered Input Container (Claude Style Card) */}
      <footer className="p-3 pt-0 relative z-20">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={handleSubmit}
            className="relative rounded-2xl border-0 card-bg p-2.5 transition-all space-y-1.5 z-20"
          >
            {/* Attached Files Chips inside the Card Container */}
            {attachedFiles.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pb-2 border-0">
                {attachedFiles.map((file) => {
                  const ext = (file.filename?.split('.').pop() || 'FILE').toUpperCase();
                  const isImage = ['PNG', 'JPG', 'JPEG', 'WEBP', 'GIF', 'SVG'].includes(ext);

                  return (
                    <div key={file.file_id} className="flex items-center gap-2 rounded-xl border-0 bg-[var(--bg-input)] px-2.5 py-1 text-xs theme-text-primary">
                      <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider ${
                        isImage ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'
                      }`}>
                        {ext}
                      </span>
                      <span className="truncate max-w-[180px] font-medium text-[11px]">{file.filename}</span>
                      <button
                        type="button"
                        onClick={() => removeAttachedFile(file.file_id)}
                        className="ml-0.5 rounded p-0.5 theme-text-muted hover:bg-[var(--bg-hover)] hover:theme-text-primary transition-colors border-0 bg-transparent cursor-pointer"
                        title="Remove attachment"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Compact Multiline Textarea (No Scrollbar) */}
            <textarea
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              disabled={isStreaming}
              placeholder="Message Sovereign Agent..."
              rows={1}
              className="w-full resize-none border-0 bg-transparent px-1 py-0.5 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none focus:ring-0 leading-relaxed disabled:opacity-50 font-sans min-h-[32px] max-h-[140px] overflow-hidden"
            />

            {/* Compact Bottom Toolbar Row */}
            <div className="flex items-center justify-between pt-1 border-0">
              {/* Left Action Controls */}
              <div className="flex items-center gap-1.5">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  multiple
                />

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isStreaming || isUploading}
                  className="flex h-6.5 w-6.5 items-center justify-center rounded-lg theme-text-muted hover:bg-[var(--bg-hover)] hover:theme-text-primary transition-colors disabled:opacity-40 border-0 bg-transparent cursor-pointer"
                  title="Attach Files"
                >
                  {isUploading ? <Loader2 className="h-3.5 w-3.5 animate-spin theme-text-secondary" /> : <Paperclip className="h-3.5 w-3.5" />}
                </button>

                {onToggleThinking && (
                  <button
                    type="button"
                    onClick={onToggleThinking}
                    disabled={isStreaming || selectedModelMode === 'coding'}
                    className={`flex h-6.5 items-center rounded-lg px-2 text-[11px] font-medium transition-colors border-0 cursor-pointer ${
                      selectedModelMode === 'coding'
                        ? 'input-bg theme-text-muted opacity-40 cursor-not-allowed'
                        : isThinkingMode
                        ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-semibold'
                        : 'input-bg theme-text-muted hover:theme-text-primary'
                    }`}
                    title={selectedModelMode === 'coding' ? "Thinking is disabled for Coding Model" : (isThinkingMode ? "Disable Thinking Mode" : "Enable Thinking Mode")}
                  >
                    Think
                  </button>
                )}

                {/* Custom Theme-Aware Model Selector Dropdown (No Emojis) */}
                <div className="relative" ref={modelMenuRef}>
                  <button
                    type="button"
                    onClick={() => setShowModelMenu(!showModelMenu)}
                    disabled={isStreaming}
                    className="flex h-6.5 items-center gap-1 rounded-lg input-bg px-2 text-[11px] font-medium theme-text-muted hover:theme-text-primary transition-colors border-0 cursor-pointer disabled:opacity-40"
                    title="Select Model / Router Mode"
                  >
                    <span>
                      {(modelConfig?.options?.find((o) => o.id === selectedModelMode)?.label) || (selectedModelMode === 'coding' ? 'Coding' : selectedModelMode === 'reasoning' ? 'Reasoning' : 'Auto (Router)')}
                    </span>
                    <ChevronDown className="h-3 w-3 theme-text-muted shrink-0" />
                  </button>

                  {showModelMenu && (
                    <div className="absolute bottom-full mb-2 left-0 z-50 w-56 rounded-xl card-bg border-0 p-1 font-sans text-xs space-y-0.5">
                      {(modelConfig?.options || [
                        { id: 'auto', label: 'Auto (Router)', desc: 'Dynamic Waterfall Routing' },
                        { id: 'reasoning', label: 'Reasoning', desc: 'Step-by-step reasoning & math' },
                        { id: 'coding', label: 'Coding', desc: 'Code generation & execution' }
                      ]).map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => {
                            setSelectedModelMode(item.id);
                            setShowModelMenu(false);
                            if (item.id === 'coding' && isThinkingMode && onToggleThinking) {
                              onToggleThinking();
                            }
                          }}
                          className={`flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left transition-colors border-0 cursor-pointer ${
                            selectedModelMode === item.id
                              ? 'bg-[var(--bg-hover)] theme-text-primary font-semibold'
                              : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
                          }`}
                        >
                          <div>
                            <div className="font-medium text-[11px]">{item.label}</div>
                            <div className="text-[9px] theme-text-muted font-mono">{item.desc}</div>
                          </div>
                          {selectedModelMode === item.id && (
                            <Check className="h-3.5 w-3.5 text-blue-400 shrink-0 ml-2" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Action: Send Button */}
              <button
                type="submit"
                disabled={!canSubmit}
                className={`flex h-7 w-7 items-center justify-center rounded-full transition-all border-0 cursor-pointer ${
                  canSubmit
                    ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] hover:opacity-90'
                    : 'input-bg theme-text-muted cursor-not-allowed opacity-40'
                }`}
                title="Send Message"
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            </div>
          </form>

          <div className="mt-1.5 text-center text-[10px] theme-text-muted font-mono">
            Sovereign Agent running locally on air-gapped open-weight LLMs.
          </div>
        </div>
      </footer>
        </>
      )}

      {/* Sovereign Air-Gap Network Security Telemetry Audit Modal */}
      {showAirGapModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl card-bg p-6 border-0 theme-text-primary space-y-4">
            <div className="flex items-center justify-between border-0 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 theme-text-secondary" />
                <h3 className="text-base font-bold theme-text-primary">
                  Sovereign Air-Gap Security Telemetry
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAirGapModal(false)}
                className="rounded-lg p-1 theme-text-muted hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2.5 font-mono text-xs">
              <div className="flex justify-between items-center rounded-xl bg-[var(--bg-input)] p-3">
                <span className="theme-text-muted">Air-Gap Status:</span>
                <span className="theme-text-primary font-bold flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-[var(--text-primary)] animate-pulse" />
                  {netTelemetry?.status || '100% AIR_GAPPED_ISOLATED'}
                </span>
              </div>
              <div className="flex justify-between items-center rounded-xl bg-[var(--bg-input)] p-3">
                <span className="theme-text-muted">Outbound WAN Egress:</span>
                <span className="theme-text-primary font-bold">{netTelemetry?.wan_egress_bytes ?? 0} Bytes (Zero Cloud Egress)</span>
              </div>
              <div className="flex justify-between items-center rounded-xl bg-[var(--bg-input)] p-3">
                <span className="theme-text-muted">External WAN Sockets:</span>
                <span className="theme-text-primary font-bold">{netTelemetry?.external_sockets ?? 0} Connections</span>
              </div>
              <div className="flex justify-between items-center rounded-xl bg-[var(--bg-input)] p-3">
                <span className="theme-text-muted">Local On-Premise Services:</span>
                <span className="theme-text-secondary font-bold">FastAPI (:8000), Postgres (:5432), Ollama (:11434)</span>
              </div>
            </div>

            <div className="rounded-xl card-bg p-3 border-0 text-[11px] theme-text-muted leading-relaxed font-sans space-y-1">
              <strong className="theme-text-primary font-semibold">Empirical Sovereign Proof:</strong>
              <p>All LLM inference, pgvector embedding queries, Python sandbox executions, and document generation run 100% locally on your internal loopback interfaces. No telemetry or data packets are transmitted externally.</p>
            </div>

            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={() => setShowAirGapModal(false)}
                className="rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 transition-all border-0 cursor-pointer"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sovereign Knowledge Base (RAG) Management Modal */}
      {showKbModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-2xl rounded-2xl card-bg p-6 border-0 theme-text-primary space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-0 pb-3">
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-[var(--text-secondary)]" />
                <h3 className="text-base font-bold theme-text-primary">
                  Sovereign Knowledge Base (RAG Ingestion)
                </h3>
              </div>
              <button
                type="button"
                onClick={onCloseKbModal}
                className="rounded-lg p-1 theme-text-muted hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs theme-text-muted">
              Ingest internal enterprise SOPs, technical manuals, or standards into offline <strong>ChromaDB</strong> vector store powered by local <code>nomic-embed-text</code> embeddings.
            </p>

            {/* Drag & Drop Upload Container */}
            <div className="rounded-xl border-0 p-4 text-center bg-[var(--bg-input)]">
              <input
                type="file"
                ref={kbFileInputRef}
                onChange={handleKbFileUpload}
                className="hidden"
                accept=".pdf,.docx,.txt,.csv,.md"
                multiple
              />
              <UploadCloud className="mx-auto h-8 w-8 theme-text-muted mb-2" />
              <div className="text-xs font-semibold theme-text-primary">
                {isIngestingKb ? "Chunking & Embedding Document..." : "Click or drag & drop enterprise SOP files"}
              </div>
              <div className="text-[11px] theme-text-muted mt-1">
                Supports PDF, DOCX, TXT, CSV manuals (Layout-aware chunking)
              </div>
              <button
                type="button"
                onClick={() => kbFileInputRef.current?.click()}
                disabled={isIngestingKb}
                className="mt-3 rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-1.5 text-xs font-medium hover:opacity-90 transition-all border-0 cursor-pointer disabled:opacity-50"
              >
                {isIngestingKb ? "Ingesting..." : "Select SOP Files"}
              </button>
            </div>

            {/* Live Ingested Reference Document List */}
            <div className="flex-1 overflow-y-auto space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold theme-text-primary px-1">
                <span>Ingested Reference Documents</span>
                <span className="font-mono text-[11px] theme-text-muted">
                  {kbData.total_documents} docs · {kbData.total_chunks} vector chunks
                </span>
              </div>

              {kbData.files.length === 0 ? (
                <div className="py-6 text-center text-xs theme-text-muted">
                  No documents ingested yet. Upload an SOP to populate the RAG database.
                </div>
              ) : (
                kbData.files.map((file) => (
                  <div key={file.source} className="flex items-center justify-between rounded-xl bg-[var(--bg-input)] p-3 text-xs border-0">
                    <div className="flex items-center gap-2.5 truncate">
                      <FileText className="h-4 w-4 theme-text-secondary shrink-0" />
                      <div className="truncate">
                        <div className="font-medium theme-text-primary truncate">{file.source}</div>
                        <div className="text-[10px] theme-text-muted font-mono mt-0.5">
                          {file.chunk_count} vector chunks · {Array.from(file.section_types || []).join(', ') || 'text'}
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteKbFile(file.source)}
                      className="rounded p-1.5 theme-text-muted hover:bg-[var(--bg-hover)] hover:text-red-400 transition-colors border-0 bg-transparent cursor-pointer"
                      title={`Remove ${file.source} from RAG KB`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end pt-2 border-0">
              <button
                type="button"
                onClick={onCloseKbModal}
                className="rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 transition-all border-0 cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* In-App File Preview Modal */}
      {previewFile && (
        <FilePreviewModal
          file={previewFile}
          onClose={() => setPreviewFile(null)}
        />
      )}

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl card-bg p-6 border-0 theme-text-primary space-y-4 shadow-lg">
            <div className="flex items-center justify-between pb-2">
              <h3 className="text-base font-bold theme-text-primary flex items-center gap-2">
                <Key className="h-4 w-4 theme-text-secondary" />
                <span>Change Password</span>
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowPasswordModal(false);
                  setPwdStatus(null);
                }}
                className="rounded-lg p-1.5 theme-text-muted hover:bg-[var(--bg-hover)] border-0 bg-transparent cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {pwdStatus && (
              <div className={`rounded-xl p-3 text-xs font-medium ${
                pwdStatus.type === 'success' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
              }`}>
                {pwdStatus.message}
              </div>
            )}

            <form onSubmit={handleChangePasswordSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-medium theme-text-muted block mb-1">Current Password</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-medium theme-text-muted block mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-medium theme-text-muted block mb-1">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordModal(false);
                    setPwdStatus(null);
                  }}
                  className="rounded-xl px-4 py-2 text-xs font-semibold theme-text-muted hover:bg-[var(--bg-hover)] border-0 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isChangingPwd}
                  className="rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 border-0 cursor-pointer disabled:opacity-50"
                >
                  {isChangingPwd ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
