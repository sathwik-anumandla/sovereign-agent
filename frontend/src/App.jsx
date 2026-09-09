import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import AdminPanelModal from './components/AdminPanelModal';
import AdminDashboardView from './components/AdminDashboardView';
import LoginScreen from './components/LoginScreen';
import TwoFactorAuthModal from './components/TwoFactorAuthModal';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('workbench_token'));
  const [currentUser, setCurrentUser] = useState(null);
  const [isVerifyingAuth, setIsVerifyingAuth] = useState(true);

  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [toolCallsMap, setToolCallsMap] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [routeDecision, setRouteDecision] = useState(null);
  const [modelConfig, setModelConfig] = useState(null);
  const [isThinkingMode, setIsThinkingMode] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('workbench_theme') || 'dark');
  const [showKbModal, setShowKbModal] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [show2faModal, setShow2faModal] = useState(false);

  const [users, setUsers] = useState([]);

  // Sync data-theme attribute on <html> element whenever theme changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('workbench_theme', theme);
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Verify token & fetch user profile on boot
  useEffect(() => {
    verifyAuthentication();
  }, [token]);

  const verifyAuthentication = async () => {
    if (!token) {
      setCurrentUser(null);
      setIsVerifyingAuth(false);
      return;
    }

    try {
      setIsVerifyingAuth(true);
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const user = await res.json();
        setCurrentUser(user);
        if (user.role === 'admin') {
          await fetchUsers(token);
        }
        await loadThreads(user.user_id, false, token);
        await fetchModelConfig(token);
      } else {
        localStorage.removeItem('workbench_token');
        setToken(null);
        setCurrentUser(null);
      }
    } catch (err) {
      console.error('Error verifying auth:', err);
    } finally {
      setIsVerifyingAuth(false);
    }
  };

  const fetchUsers = async (authToken = token) => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_BASE}/users`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Error fetching users:', err);
    }
  };

  const fetchModelConfig = async (authToken = token) => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_BASE}/config/models`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setModelConfig(data);
      }
    } catch (err) {
      console.error('Error fetching model config:', err);
    }
  };

  const handleLoginSuccess = async (newToken, userProfile) => {
    localStorage.setItem('workbench_token', newToken);
    setToken(newToken);
    setCurrentUser(userProfile);
    if (userProfile.role === 'admin') {
      await fetchUsers(newToken);
    }
    await loadThreads(userProfile.user_id, false, newToken);
    await fetchModelConfig(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('workbench_token');
    setToken(null);
    setCurrentUser(null);
    setThreads([]);
    setActiveThreadId(null);
    setMessages([]);
  };

  const loadThreads = async (targetUserId = currentUser?.user_id, preserveActiveId = false, authToken = token) => {
    if (!authToken) return;
    try {
      const url = targetUserId ? `${API_BASE}/threads?user_id=${targetUserId}` : `${API_BASE}/threads`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setThreads(data);
        if (!preserveActiveId && data.length > 0 && !activeThreadId) {
          handleSelectThread(data[0].thread_id, authToken);
        }
      }
    } catch (err) {
      console.error('Error loading threads:', err);
    }
  };

  const handleNewThread = async () => {
    if (!currentUser || !token) return;
    try {
      const res = await fetch(`${API_BASE}/threads`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ user_id: currentUser.user_id })
      });
      if (res.ok) {
        const data = await res.json();
        const tid = data.thread_id;
        
        setActiveThreadId(tid);
        setMessages([]);
        setToolCallsMap([]);
        setRouteDecision(null);
        setConnectionError(null);

        const newThreadObj = {
          thread_id: tid,
          preview: 'New Conversation',
          updated_at: '',
          user_id: currentUser.user_id,
          user_name: currentUser.name,
          user_role: currentUser.role
        };
        setThreads((prev) => [newThreadObj, ...prev.filter((t) => t.thread_id !== tid)]);
      }
    } catch (err) {
      console.error('Error creating thread:', err);
    }
  };

  const handleDeleteThread = async (threadId) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/threads/${threadId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        if (activeThreadId === threadId) {
          setActiveThreadId(null);
          setMessages([]);
        }
        await loadThreads(currentUser?.user_id, true, token);
      }
    } catch (err) {
      console.error(`Error deleting thread ${threadId}:`, err);
    }
  };

  const handleSelectThread = async (threadId, authToken = token) => {
    if (!authToken) return;
    setActiveThreadId(threadId);
    setConnectionError(null);
    setToolCallsMap([]);
    setRouteDecision(null);

    try {
      const res = await fetch(`${API_BASE}/threads/${threadId}/history`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRouteDecision(data.route_decision || null);

        const uiMessages = [];
        const rawMsgs = data.messages || [];
        const toolResults = data.tool_results || [];

        let currentToolIndex = 0;
        let currentAssistantTurn = null;

        for (const msg of rawMsgs) {
          if (!msg || msg.role === 'system' || msg.role === 'tool') {
            continue;
          }

          if (msg.role === 'user') {
            if (currentAssistantTurn && (currentAssistantTurn.content || currentAssistantTurn.toolCalls.length > 0)) {
              uiMessages.push(currentAssistantTurn);
              currentAssistantTurn = null;
            }

            const attachedFiles = msg.attachedFiles || msg.attached_files || msg.files || (uiMessages.length === 0 ? (data.files || []) : []);
            if (msg.content || (attachedFiles && attachedFiles.length > 0)) {
              uiMessages.push({
                role: 'user',
                content: msg.content,
                attachedFiles: attachedFiles
              });
            }
          } else if (msg.role === 'assistant') {
            if (!currentAssistantTurn) {
              currentAssistantTurn = {
                role: 'assistant',
                content: '',
                toolCalls: [],
                planSteps: data.plan_steps || [],
                routeDecision: data.route_decision || null,
                durationSeconds: data.duration_seconds || null
              };
            }

            if (msg.content) {
              currentAssistantTurn.content = currentAssistantTurn.content
                ? currentAssistantTurn.content + '\n' + msg.content
                : msg.content;
            }

            const rawCalls = msg.tool_calls || [];
            if (rawCalls.length > 0) {
              for (const call of rawCalls) {
                const func = call.function || call;
                const tName = func.name || call.name || 'tool';
                const tInput = func.arguments || call.arguments || {};

                const matchingResult = toolResults[currentToolIndex];
                if (matchingResult) {
                  currentToolIndex++;
                  currentAssistantTurn.toolCalls.push({
                    tool_name: matchingResult.tool_name || tName,
                    success: matchingResult.success,
                    status: matchingResult.success ? 'success' : 'error',
                    output_summary: matchingResult.output_summary,
                    raw_output: matchingResult.raw_output,
                    isRunning: false
                  });
                } else {
                  currentAssistantTurn.toolCalls.push({
                    tool_name: tName,
                    tool_input: tInput,
                    isRunning: false
                  });
                }
              }
            }
          }
        }

        if (currentAssistantTurn && (currentAssistantTurn.content || currentAssistantTurn.toolCalls.length > 0)) {
          uiMessages.push(currentAssistantTurn);
        }

        // Fallback if uiMessages is empty but prompt exists
        if (uiMessages.length === 0 && data.prompt) {
          uiMessages.push({
            role: 'user',
            content: data.prompt
          });
          if (data.response) {
            uiMessages.push({
              role: 'assistant',
              content: data.response,
              toolCalls: toolResults.map((tr) => ({
                tool_name: tr.tool_name,
                success: tr.success,
                status: tr.success ? 'success' : 'error',
                output_summary: tr.output_summary,
                raw_output: tr.raw_output,
                isRunning: false
              })),
              planSteps: data.plan_steps || [],
              routeDecision: data.route_decision || null,
              durationSeconds: data.duration_seconds || null
            });
          }
        }

        setMessages(uiMessages);
      }
    } catch (err) {
      console.error(`Error loading history for thread ${threadId}:`, err);
    }
  };

  const handleFileUpload = async (file) => {
    if (!activeThreadId || !token) return null;
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/threads/${activeThreadId}/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.error('File upload error:', err);
      throw err;
    }
    return null;
  };

  const handleSendMessage = async (content, fileIds, attachedFiles, modelOverride = 'auto') => {
    if (!activeThreadId || isStreaming || !token) return;

    setConnectionError(null);
    setIsStreaming(true);
    setToolCallsMap([]);

    const newMessages = [
      ...messages,
      {
        role: 'user',
        content: content,
        attachedFiles: attachedFiles || []
      }
    ];
    setMessages(newMessages);

    const assistantIndex = newMessages.length;
    let currentAssistantText = '';
    let activeTools = [];
    let dynamicPlanSteps = [];

    const modelTag = modelConfig?.models?.[modelOverride]?.tag || modelConfig?.options?.find(o => o.id === modelOverride)?.model_tag;
    const initialRouteDecision = (modelOverride && modelOverride !== 'auto')
      ? {
          role: modelOverride,
          model: modelTag || (modelOverride === 'coding' ? 'qwen2.5-coder:3b' : 'qwen3.5:4b-q4_K_M'),
          method: 'manual_override'
        }
      : null;

    let activeRouteDecision = initialRouteDecision;
    setRouteDecision(initialRouteDecision);

    try {
      const response = await fetch(`${API_BASE}/threads/${activeThreadId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          content: content,
          file_ids: fileIds,
          files: attachedFiles,
          thinking: isThinkingMode,
          model_override: modelOverride
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'message';
      let currentData = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const val = trimmed.slice(5).trim();
            currentData = currentData ? currentData + '\n' + val : val;
          } else if (trimmed === '') {
            if (currentData) {
              try {
                const parsedData = JSON.parse(currentData);

                if (currentEvent === 'status') {
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[assistantIndex] = {
                      ...updated[assistantIndex],
                      role: 'assistant',
                      status: parsedData
                    };
                    return updated;
                  });
                } else if (currentEvent === 'route_decision') {
                  activeRouteDecision = parsedData;
                  setRouteDecision(parsedData);
                } else if (currentEvent === 'plan') {
                  dynamicPlanSteps = parsedData.steps || [];
                } else if (currentEvent === 'token') {
                  currentAssistantText += parsedData.content;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[assistantIndex] = {
                      role: 'assistant',
                      content: currentAssistantText,
                      toolCalls: activeTools,
                      planSteps: dynamicPlanSteps,
                      routeDecision: activeRouteDecision,
                      hasStartedTokens: true
                    };
                    return updated;
                  });
                } else if (currentEvent === 'tool_call_start') {
                  activeTools = [
                    ...activeTools,
                    {
                      tool_name: parsedData.tool_name,
                      tool_input: parsedData.tool_input,
                      isRunning: true
                    }
                  ];
                  setToolCallsMap([...activeTools]);
                } else if (currentEvent === 'tool_call_result') {
                  activeTools = activeTools.map((tc) => {
                    if (tc.tool_name === parsedData.tool_name && tc.isRunning) {
                      return {
                        ...tc,
                        isRunning: false,
                        success: parsedData.success,
                        output_summary: parsedData.output_summary,
                        raw_output: parsedData.raw_output
                      };
                    }
                    return tc;
                  });
                  setToolCallsMap([...activeTools]);
                } else if (currentEvent === 'final') {
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[assistantIndex] = {
                      role: 'assistant',
                      content: parsedData.content || currentAssistantText,
                      toolCalls: activeTools,
                      planSteps: parsedData.plan_steps || dynamicPlanSteps,
                      routeDecision: parsedData.route_decision || activeRouteDecision,
                      durationSeconds: parsedData.duration_seconds,
                      hasStartedTokens: true
                    };
                    return updated;
                  });
                } else if (currentEvent === 'error') {
                  setConnectionError(parsedData.message || 'Stream processing error');
                }
              } catch (parseErr) {
                console.error('Error parsing SSE JSON:', parseErr, currentData);
              }
              currentEvent = 'message';
              currentData = '';
            }
          }
        }
      }
    } catch (err) {
      console.error('Streaming error:', err);
      setConnectionError('Connection lost or stream interrupted. Please retry.');
    } finally {
      setIsStreaming(false);
      setToolCallsMap([]);
      await loadThreads(currentUser?.user_id, true, token);
    }
  };

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  if (isVerifyingAuth) {
    return (
      <div className="flex h-screen w-screen items-center justify-center app-bg theme-text-primary text-xs font-mono">
        Verifying Sovereign Air-Gap Security Credentials...
      </div>
    );
  }

  if (!currentUser) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  if (currentUser.role === 'admin') {
    return (
      <AdminDashboardView
        currentUser={currentUser}
        token={token}
        onLogout={handleLogout}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />
    );
  }

  const activeThreadObj = threads.find((t) => t.thread_id === activeThreadId);
  const activeThreadTitle = activeThreadObj ? (activeThreadObj.title || activeThreadObj.preview || activeThreadObj.first_prompt) : 'Sovereign Agent';

  return (
    <div className="flex h-screen w-screen overflow-hidden app-bg">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={(id) => handleSelectThread(id, token)}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        onOpenKbModal={() => setShowKbModal(true)}
        onOpenAdminModal={() => setShowAdminModal(true)}
        onOpen2faModal={() => setShow2faModal(true)}
        currentUser={currentUser}
        onLogout={handleLogout}
        isOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        token={token}
      />
      <ChatWindow
        activeThreadId={activeThreadId}
        activeThreadTitle={activeThreadTitle}
        messages={messages}
        toolCallsMap={toolCallsMap}
        isStreaming={isStreaming}
        connectionError={connectionError}
        routeDecision={routeDecision}
        onSendMessage={handleSendMessage}
        onFileUpload={handleFileUpload}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        isThinkingMode={isThinkingMode}
        onToggleThinking={() => setIsThinkingMode((prev) => !prev)}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        showKbModal={showKbModal}
        onCloseKbModal={() => setShowKbModal(false)}
        token={token}
        modelConfig={modelConfig}
      />
      <AdminPanelModal
        isOpen={showAdminModal}
        onClose={() => setShowAdminModal(false)}
        token={token}
      />
      <TwoFactorAuthModal
        isOpen={show2faModal}
        onClose={() => setShow2faModal(false)}
        token={token}
        currentUser={currentUser}
      />
    </div>
  );
}
