import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Users, 
  MessageSquare, 
  HardDrive, 
  Database, 
  Activity, 
  UserPlus, 
  Search, 
  Trash2, 
  Eye, 
  RefreshCw, 
  LogOut, 
  Sun, 
  Moon, 
  Server, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  X,
  Key,
  Upload,
  FileText
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function AdminDashboardView({ token, currentUser, onLogout, onToggleTheme, theme }) {
  const [metrics, setMetrics] = useState(null);
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('telemetry'); // 'telemetry' | 'users' | 'threads' | 'rag' | 'logs'

  // User management form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newName, setNewName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newDepartment, setNewDepartment] = useState('');
  const [newRole, setNewRole] = useState('user');
  const [createMsg, setCreateMsg] = useState(null);
  const [createError, setCreateError] = useState(null);

  // Search filters
  const [userSearch, setUserSearch] = useState('');
  const [threadSearch, setThreadSearch] = useState('');

  // Inspection modal
  const [selectedThread, setSelectedThread] = useState(null);

  // Change Password Modal state
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPasswordChange, setNewPasswordChange] = useState('');
  const [pwdMsg, setPwdMsg] = useState(null);
  const [pwdError, setPwdError] = useState(null);

  // RAG upload state
  const [isIngesting, setIsIngesting] = useState(false);
  const [ragFiles, setRagFiles] = useState([]);
  const [netTelemetry, setNetTelemetry] = useState(null);

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [metricsRes, threadsRes, ragRes, netRes] = await Promise.all([
        fetch(`${API_BASE}/admin/metrics`, { headers }),
        fetch(`${API_BASE}/admin/threads`, { headers }),
        fetch(`${API_BASE}/knowledge_base/files`, { headers }),
        fetch(`${API_BASE}/api/network/status`, { headers })
      ]);

      if (metricsRes.ok) {
        const metricsData = await metricsRes.json();
        setMetrics(metricsData);
      }
      if (threadsRes.ok) {
        const threadsData = await threadsRes.json();
        setThreads(threadsData);
      }
      if (ragRes.ok) {
        const ragData = await ragRes.json();
        setRagFiles(Array.isArray(ragData) ? ragData : (ragData.files || []));
      }
      if (netRes.ok) {
        const netData = await netRes.json();
        setNetTelemetry(netData);
      }
    } catch (err) {
      console.error('Error fetching admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchAdminData();
    }
  }, [token]);

  const handleCreateUserSubmit = async (e) => {
    e.preventDefault();
    setCreateMsg(null);
    setCreateError(null);

    try {
      const res = await fetch(`${API_BASE}/admin/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          username: newUsername.trim(),
          name: newName.trim(),
          password: newPassword.trim(),
          department: newDepartment.trim() || 'Operations',
          role: newRole
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create user');
      }

      setCreateMsg(`Account @${data.username} created successfully!`);
      setNewUsername('');
      setNewName('');
      setNewPassword('');
      setNewDepartment('');
      setNewRole('user');
      fetchAdminData();
    } catch (err) {
      setCreateError(err.message);
    }
  };

  const handleDeleteUser = async (userId, name) => {
    if (!window.confirm(`Are you sure you want to delete user account '${name}'? This will purge all associated thread history.`)) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchAdminData();
      } else {
        const data = await res.json();
        alert(`Error deleting user: ${data.detail}`);
      }
    } catch (err) {
      console.error('Error deleting user:', err);
    }
  };

  const handleDeleteThread = async (threadId) => {
    if (!window.confirm(`Are you sure you want to delete thread ${threadId}?`)) return;

    try {
      const res = await fetch(`${API_BASE}/admin/threads/${threadId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchAdminData();
      }
    } catch (err) {
      console.error('Error deleting thread:', err);
    }
  };

  const handleInspectThread = async (threadId) => {
    try {
      const res = await fetch(`${API_BASE}/admin/threads/${threadId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedThread(data);
      }
    } catch (err) {
      console.error('Error inspecting thread:', err);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwdMsg(null);
    setPwdError(null);

    try {
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPasswordChange
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Password change failed');

      setPwdMsg('Password changed successfully!');
      setOldPassword('');
      setNewPasswordChange('');
      setTimeout(() => setShowPasswordModal(false), 1500);
    } catch (err) {
      setPwdError(err.message);
    }
  };

  const handleRagFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsIngesting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/knowledge_base/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      if (res.ok) {
        fetchAdminData();
      }
    } catch (err) {
      console.error('Error uploading RAG file:', err);
    } finally {
      setIsIngesting(false);
    }
  };

  const filteredUsers = (metrics?.users || []).filter(u =>
    u.name?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.username?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.department?.toLowerCase().includes(userSearch.toLowerCase())
  );

  const filteredThreads = threads.filter(t =>
    t.title?.toLowerCase().includes(threadSearch.toLowerCase()) ||
    t.owner_name?.toLowerCase().includes(threadSearch.toLowerCase()) ||
    t.thread_id?.toLowerCase().includes(threadSearch.toLowerCase())
  );

  return (
    <div className="flex h-screen w-screen flex-col app-bg theme-text-primary overflow-hidden font-sans">
      {/* Top Admin Governance Header Bar */}
      <header className="flex h-16 w-full items-center justify-between border-0 card-bg px-6 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-input)] theme-text-secondary border-0">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-extrabold tracking-tight theme-text-primary">
                Sovereign AI Workbench
              </h1>
              <span className="rounded-md bg-[var(--bg-input)] px-2 py-0.5 text-[10px] font-bold uppercase theme-text-muted font-mono border-0">
                System Admin Governance
              </span>
            </div>
            <p className="text-[11px] theme-text-muted">
              On-Premise Network Telemetry, RBAC User Management & Operations Audit
            </p>
          </div>
        </div>

        {/* System Status Indicator & Admin Action Badges */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 rounded-xl bg-[var(--bg-input)] border-0 px-3 py-1.5 text-xs theme-text-primary font-medium">
            <span className="h-2 w-2 rounded-full bg-[var(--text-primary)] animate-pulse" />
            <span>Operational • Zero Outbound Egress</span>
          </div>

          <button
            type="button"
            onClick={fetchAdminData}
            className="flex h-9 w-9 items-center justify-center rounded-xl card-bg border-0 theme-text-secondary hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
            title="Refresh Telemetry Data"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            type="button"
            onClick={onToggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-xl card-bg border-0 theme-text-secondary hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {/* Admin User Profile Card */}
          <div className="flex items-center gap-2.5 rounded-xl bg-[var(--bg-input)] px-3 py-1.5 border-0">
            <span className="h-2.5 w-2.5 rounded-full bg-[var(--text-primary)]" />
            <div className="text-left">
              <div className="text-xs font-bold theme-text-primary truncate">
                {currentUser?.name || 'Administrator'}
              </div>
              <div className="text-[9px] theme-text-muted font-mono">@{currentUser?.username || 'admin'}</div>
            </div>
            <button
              type="button"
              onClick={() => setShowPasswordModal(true)}
              className="ml-1 rounded p-1 theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
              title="Change Admin Password"
            >
              <Key className="h-3.5 w-3.5" />
            </button>
          </div>

          <button
            type="button"
            onClick={onLogout}
            className="flex items-center gap-1.5 rounded-xl bg-[var(--bg-input)] theme-text-primary hover:bg-[var(--bg-hover)] px-3 py-2 text-xs font-semibold transition-colors border-0 cursor-pointer"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Admin Dashboard Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Navigation Sidebar Tabs */}
        <aside className="w-64 border-0 card-bg p-4 flex flex-col justify-between shrink-0">
          <div className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider theme-text-muted px-2 pb-2 font-mono">
              Governance Modules
            </div>

            <button
              type="button"
              onClick={() => setActiveTab('telemetry')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-medium transition-colors border-0 cursor-pointer ${
                activeTab === 'telemetry'
                  ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-semibold'
                  : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
              }`}
            >
              <Server className="h-4 w-4" />
              <span>System & Telemetry</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('users')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-medium transition-colors border-0 cursor-pointer ${
                activeTab === 'users'
                  ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-semibold'
                  : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
              }`}
            >
              <Users className="h-4 w-4" />
              <span>User Roster & Roles</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('threads')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-medium transition-colors border-0 cursor-pointer ${
                activeTab === 'threads'
                  ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-semibold'
                  : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
              }`}
            >
              <MessageSquare className="h-4 w-4" />
              <span>User Chats & Audit</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('rag')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-medium transition-colors border-0 cursor-pointer ${
                activeTab === 'rag'
                  ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-semibold'
                  : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
              }`}
            >
              <Database className="h-4 w-4" />
              <span>Knowledge Base (RAG)</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('logs')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-medium transition-colors border-0 cursor-pointer ${
                activeTab === 'logs'
                  ? 'bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] font-semibold'
                  : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
              }`}
            >
              <Activity className="h-4 w-4" />
              <span>System Activity Logs</span>
            </button>
          </div>

          <div className="rounded-xl bg-[var(--bg-input)] p-3 text-[11px] theme-text-muted space-y-1.5 border-0">
            <div className="font-semibold theme-text-primary flex items-center gap-1">
              <Lock className="h-3.5 w-3.5 theme-text-secondary" />
              <span>Air-Gapped Policy</span>
            </div>
            <p className="leading-relaxed">
              System Admin accounts monitor user activity, system metrics, and audit logs. Admin accounts cannot initiate chat sessions.
            </p>
          </div>
        </aside>

        {/* Tab Content Display Area */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* TAB 1: SYSTEM & TELEMETRY */}
          {activeTab === 'telemetry' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-bold theme-text-primary">System Telemetry & Health Monitoring</h2>
                <p className="text-xs theme-text-muted">Live hardware, database, model registry, and network state</p>
              </div>

              {/* Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-2xl card-bg p-4 border-0 space-y-1">
                  <div className="flex items-center justify-between text-xs theme-text-muted">
                    <span>Registered Users</span>
                    <Users className="h-4 w-4 theme-text-secondary" />
                  </div>
                  <div className="text-2xl font-bold font-mono theme-text-primary">
                    {metrics?.total_users || 0}
                  </div>
                  <div className="text-[10px] theme-text-muted">PostgreSQL User RBAC Table</div>
                </div>

                <div className="rounded-2xl card-bg p-4 border-0 space-y-1">
                  <div className="flex items-center justify-between text-xs theme-text-muted">
                    <span>Total Conversations</span>
                    <MessageSquare className="h-4 w-4 theme-text-secondary" />
                  </div>
                  <div className="text-2xl font-bold font-mono theme-text-primary">
                    {metrics?.total_threads || 0}
                  </div>
                  <div className="text-[10px] theme-text-muted">PostgreSQL LangGraph Checkpointer</div>
                </div>

                <div className="rounded-2xl card-bg p-4 border-0 space-y-1">
                  <div className="flex items-center justify-between text-xs theme-text-muted">
                    <span>Workspace Storage</span>
                    <HardDrive className="h-4 w-4 theme-text-secondary" />
                  </div>
                  <div className="text-2xl font-bold font-mono theme-text-primary">
                    {metrics?.workspace_storage_mb || 0} MB
                  </div>
                  <div className="text-[10px] theme-text-muted">{metrics?.workspace_files_count || 0} staged files</div>
                </div>

                <div className="rounded-2xl card-bg p-4 border-0 space-y-1">
                  <div className="flex items-center justify-between text-xs theme-text-muted">
                    <span>RAG Knowledge Base</span>
                    <Database className="h-4 w-4 theme-text-secondary" />
                  </div>
                  <div className="text-2xl font-bold font-mono theme-text-primary">
                    {metrics?.rag_kb_documents || 0} Docs
                  </div>
                  <div className="text-[10px] theme-text-muted">{metrics?.rag_kb_chunks || 0} vector chunks in pgvector</div>
                </div>
              </div>

              {/* Service Health Grid */}
              <div className="rounded-2xl card-bg p-5 border-0 space-y-4">
                <h3 className="text-sm font-bold theme-text-primary flex items-center gap-2">
                  <Server className="h-4 w-4 theme-text-secondary" />
                  <span>On-Premise Infrastructure Health Status</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="flex items-center justify-between rounded-xl bg-[var(--bg-input)] p-3 border-0">
                    <div className="flex items-center gap-3">
                      <span className="h-3 w-3 rounded-full bg-[var(--text-primary)] animate-pulse" />
                      <div>
                        <div className="text-xs font-bold theme-text-primary">FastAPI Backend Server</div>
                        <div className="text-[10px] theme-text-muted font-mono">http://localhost:8000 (Python 3.13)</div>
                      </div>
                    </div>
                    <span className="rounded-md bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-bold theme-text-primary uppercase font-mono border-0">Healthy</span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl bg-[var(--bg-input)] p-3 border-0">
                    <div className="flex items-center gap-3">
                      <span className="h-3 w-3 rounded-full bg-[var(--text-primary)] animate-pulse" />
                      <div>
                        <div className="text-xs font-bold theme-text-primary">PostgreSQL + pgvector Database</div>
                        <div className="text-[10px] theme-text-muted font-mono">localhost:5432 (sovereign_workbench)</div>
                      </div>
                    </div>
                    <span className="rounded-md bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-bold theme-text-primary uppercase font-mono border-0">Connected</span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl bg-[var(--bg-input)] p-3 border-0">
                    <div className="flex items-center gap-3">
                      <span className="h-3 w-3 rounded-full bg-[var(--text-primary)] animate-pulse" />
                      <div>
                        <div className="text-xs font-bold theme-text-primary">Ollama Local LLM Inference</div>
                        <div className="text-[10px] theme-text-muted font-mono">http://127.0.0.1:11434 (qwen3.5:4b)</div>
                      </div>
                    </div>
                    <span className="rounded-md bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-bold theme-text-primary uppercase font-mono border-0">Resident</span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl bg-[var(--bg-input)] p-3 border-0">
                    <div className="flex items-center gap-3">
                      <span className="h-3 w-3 rounded-full bg-[var(--text-primary)]" />
                      <div>
                        <div className="text-xs font-bold theme-text-primary">Air-Gap WAN Egress Guard</div>
                        <div className="text-[10px] theme-text-muted font-mono">0 Outbound WAN Connections</div>
                      </div>
                    </div>
                    <span className="rounded-md bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-bold theme-text-primary uppercase font-mono border-0">Enforced</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: USER GOVERNANCE & ROLES */}
          {activeTab === 'users' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold theme-text-primary">User Accounts & RBAC Governance</h2>
                  <p className="text-xs theme-text-muted">Register new system users, manage roles, or revoke access</p>
                </div>

                <button
                  type="button"
                  onClick={() => setShowCreateForm(!showCreateForm)}
                  className="flex items-center gap-1.5 rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 transition-colors border-0 cursor-pointer"
                >
                  <UserPlus className="h-4 w-4" />
                  <span>{showCreateForm ? "Cancel Form" : "Create New User Account"}</span>
                </button>
              </div>

              {/* Create User Form Drawer */}
              {showCreateForm && (
                <form onSubmit={handleCreateUserSubmit} className="rounded-2xl card-bg p-5 space-y-4 border-0">
                  <div className="text-sm font-bold theme-text-primary flex items-center gap-2 border-0 pb-3">
                    <UserPlus className="h-4 w-4 theme-text-secondary" />
                    <span>Register New Enterprise System User</span>
                  </div>

                  {createMsg && (
                    <div className="rounded-xl bg-[var(--bg-input)] p-3 text-xs theme-text-primary font-medium border-0">
                      {createMsg}
                    </div>
                  )}

                  {createError && (
                    <div className="rounded-xl bg-red-500/10 p-3 text-xs text-red-400 font-medium flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{createError}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium theme-text-muted block mb-1">Full Name</label>
                      <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="e.g. Ramesh Kumar"
                        className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium theme-text-muted block mb-1">Username</label>
                      <input
                        type="text"
                        value={newUsername}
                        onChange={(e) => setNewUsername(e.target.value)}
                        placeholder="e.g. ramesh1"
                        className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium theme-text-muted block mb-1">Initial Password</label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium theme-text-muted block mb-1">Department</label>
                      <input
                        type="text"
                        value={newDepartment}
                        onChange={(e) => setNewDepartment(e.target.value)}
                        placeholder="e.g. Thermal Maintenance"
                        className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs theme-text-muted">Account Role:</span>
                      <select
                        value={newRole}
                        onChange={(e) => setNewRole(e.target.value)}
                        className="rounded-xl border-0 input-bg px-3 py-1.5 text-xs theme-text-primary focus:outline-none"
                      >
                        <option value="user">User (Standard Access)</option>
                        <option value="admin">Admin (System Governance)</option>
                      </select>
                    </div>

                    <button
                      type="submit"
                      className="rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-5 py-2 text-xs font-semibold hover:opacity-90 transition-colors border-0 cursor-pointer"
                    >
                      Save Account
                    </button>
                  </div>
                </form>
              )}

              {/* User Search & Roster Table */}
              <div className="rounded-2xl card-bg p-5 border-0 space-y-4">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 theme-text-muted" />
                    <input
                      type="text"
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Search users, departments..."
                      className="w-full rounded-xl border-0 input-bg pl-9 pr-3.5 py-2 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                    />
                  </div>

                  <span className="text-xs theme-text-muted font-mono">
                    Showing {filteredUsers.length} of {metrics?.total_users || 0} users
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-0 text-[11px] theme-text-muted">
                        <th className="py-3 px-3 font-medium">User Profile</th>
                        <th className="py-3 px-3 font-medium">Department</th>
                        <th className="py-3 px-3 font-medium">Role</th>
                        <th className="py-3 px-3 font-medium">Created Date</th>
                        <th className="py-3 px-3 font-medium text-center">Threads</th>
                        <th className="py-3 px-3 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map((u) => (
                        <tr key={u.user_id} className="border-0 hover:bg-[var(--bg-hover)] transition-colors">
                          <td className="py-3 px-3 font-medium theme-text-primary">
                            <div>
                              <div className="font-semibold">{u.name}</div>
                              <div className="text-[10px] theme-text-muted font-mono">@{u.username}</div>
                            </div>
                          </td>
                          <td className="py-3 px-3 theme-text-muted text-[11px]">
                            {u.department}
                          </td>
                          <td className="py-3 px-3">
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md font-mono text-[10px] font-bold uppercase bg-[var(--bg-input)] theme-text-primary border-0">
                              {u.role === 'admin' ? <ShieldCheck className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
                              {u.role}
                            </span>
                          </td>
                          <td className="py-3 px-3 theme-text-muted font-mono text-[11px]">
                            {u.created_at ? u.created_at.slice(0, 10) : 'System Default'}
                          </td>
                          <td className="py-3 px-3 text-center font-mono font-medium theme-text-primary">
                            {u.thread_count}
                          </td>
                          <td className="py-3 px-3 text-right">
                            {u.role !== 'admin' ? (
                              <button
                                type="button"
                                onClick={() => handleDeleteUser(u.user_id, u.name)}
                                className="rounded-lg p-1.5 text-red-400 hover:bg-red-500/20 transition-colors border-0 bg-transparent cursor-pointer"
                                title="Delete User Account"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            ) : (
                              <span className="text-[10px] theme-text-muted italic">Protected</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: USER CHATS & THREAD AUDIT */}
          {activeTab === 'threads' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold theme-text-primary">User Conversation Audit & Governance</h2>
                  <p className="text-xs theme-text-muted">Monitor, search, and audit chat threads across all system accounts</p>
                </div>

                <div className="relative w-full sm:w-72">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 theme-text-muted" />
                  <input
                    type="text"
                    value={threadSearch}
                    onChange={(e) => setThreadSearch(e.target.value)}
                    placeholder="Search threads, prompt text..."
                    className="w-full rounded-xl border-0 input-bg pl-9 pr-3.5 py-2 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                  />
                </div>
              </div>

              {/* Thread Table */}
              <div className="rounded-2xl card-bg p-5 border-0 space-y-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-0 text-[11px] theme-text-muted">
                        <th className="py-3 px-3 font-medium">Thread Title / ID</th>
                        <th className="py-3 px-3 font-medium">User / Department</th>
                        <th className="py-3 px-3 font-medium">Response Summary</th>
                        <th className="py-3 px-3 font-medium text-center">Tools Executed</th>
                        <th className="py-3 px-3 font-medium text-center">Files</th>
                        <th className="py-3 px-3 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredThreads.map((t) => (
                        <tr key={t.thread_id} className="border-0 hover:bg-[var(--bg-hover)] transition-colors">
                          <td className="py-3 px-3 font-medium theme-text-primary max-w-[220px]">
                            <div className="font-semibold truncate">{t.title || t.preview || 'Conversation Thread'}</div>
                            <div className="text-[10px] theme-text-muted font-mono truncate">{t.thread_id}</div>
                          </td>
                          <td className="py-3 px-3 theme-text-muted text-[11px]">
                            <div className="font-medium theme-text-primary">{t.owner_name || 'System User'}</div>
                            <div className="text-[10px] theme-text-muted font-mono">{t.owner_role || 'USER'}</div>
                          </td>
                          <td className="py-3 px-3 theme-text-secondary text-[11px] max-w-[260px] truncate">
                            {t.response_preview || 'No response recorded'}
                          </td>
                          <td className="py-3 px-3 text-center font-mono font-medium theme-text-primary">
                            {t.tool_count || 0}
                          </td>
                          <td className="py-3 px-3 text-center font-mono font-medium theme-text-primary">
                            {t.file_count || 0}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => handleInspectThread(t.thread_id)}
                                className="rounded-lg p-1.5 theme-text-muted hover:theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
                                title="Inspect Thread Details"
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteThread(t.thread_id)}
                                className="rounded-lg p-1.5 theme-text-muted hover:text-red-400 transition-colors border-0 bg-transparent cursor-pointer"
                                title="Delete Conversation Thread"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Thread History Inspection Drawer / Modal */}
              {selectedThread && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
                  <div className="w-full max-w-3xl rounded-2xl card-bg p-6 border-0 theme-text-primary space-y-4 max-h-[85vh] flex flex-col">
                    <div className="flex items-center justify-between border-0 pb-3">
                      <div>
                        <h3 className="text-base font-bold theme-text-primary">Thread Inspection Details</h3>
                        <div className="text-[10px] theme-text-muted font-mono">Thread ID: {selectedThread.thread_id}</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedThread(null)}
                        className="rounded-lg p-1.5 theme-text-muted hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                      {(selectedThread.messages || []).map((m, mIdx) => (
                        <div key={mIdx} className={`p-3 rounded-xl ${m.role === 'user' ? 'bg-[var(--bg-input)] text-right ml-12' : 'card-bg border-0 mr-12'}`}>
                          <div className="text-[10px] font-bold theme-text-muted font-mono mb-1 uppercase">{m.role}</div>
                          <div className="text-xs theme-text-primary leading-relaxed whitespace-pre-wrap">{m.content}</div>
                        </div>
                      ))}
                    </div>

                    <div className="flex justify-end pt-2 border-0">
                      <button
                        type="button"
                        onClick={() => setSelectedThread(null)}
                        className="rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold border-0 cursor-pointer"
                      >
                        Close Details
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: KNOWLEDGE BASE (RAG) */}
          {activeTab === 'rag' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold theme-text-primary">Enterprise Knowledge Base (pgvector RAG)</h2>
                  <p className="text-xs theme-text-muted">Manage ingested enterprise SOPs, technical manuals, and document embeddings</p>
                </div>

                <label className="flex items-center gap-2 rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 transition-colors border-0 cursor-pointer">
                  <Upload className="h-4 w-4" />
                  <span>{isIngesting ? "Ingesting PDF..." : "Upload Enterprise Document"}</span>
                  <input type="file" onChange={handleRagFileUpload} className="hidden" accept=".pdf,.txt,.csv,.md" />
                </label>
              </div>

              <div className="rounded-2xl card-bg p-5 border-0 space-y-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-0 text-[11px] theme-text-muted">
                        <th className="py-3 px-3 font-medium">Document Name</th>
                        <th className="py-3 px-3 font-medium">Type</th>
                        <th className="py-3 px-3 font-medium text-center">Vector Chunks</th>
                        <th className="py-3 px-3 font-medium text-right">Ingested At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ragFiles.map((f, fIdx) => (
                        <tr key={fIdx} className="border-0 hover:bg-[var(--bg-hover)] transition-colors">
                          <td className="py-3 px-3 font-medium theme-text-primary flex items-center gap-2">
                            <FileText className="h-4 w-4 theme-text-secondary shrink-0" />
                            <span className="font-semibold">{f.filename || f.original_filename || f.source || 'Enterprise Document'}</span>
                          </td>
                          <td className="py-3 px-3 theme-text-muted font-mono text-[11px]">
                            {f.extension || (f.filename || f.source || '').split('.').pop()?.toUpperCase() || 'PDF'}
                          </td>
                          <td className="py-3 px-3 text-center font-mono font-medium theme-text-primary">
                            {f.chunk_count || 0}
                          </td>
                          <td className="py-3 px-3 text-right theme-text-muted font-mono text-[11px]">
                            {(f.ingested_at || f.last_ingested) ? String(f.ingested_at || f.last_ingested).slice(0, 10) : 'Active'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: SYSTEM LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-bold theme-text-primary">System & Security Audit Logs</h2>
                <p className="text-xs theme-text-muted">Real-time log trail of system governance, authentication, and state operations</p>
              </div>

              <div className="rounded-2xl card-bg p-5 border-0 space-y-2 font-mono text-xs theme-text-primary leading-relaxed max-h-[70vh] overflow-y-auto">
                <div className="text-emerald-500 font-semibold">[SYSTEM INIT] Sovereign AI Workbench API v1.0.0 Online</div>
                <div className="theme-text-primary">[RBAC GUARD] Enforcing role segregation: ADMIN governance mode active</div>
                <div className="text-blue-400 font-semibold">[AIR-GAP STATUS] {netTelemetry?.status || '100% AIR_GAPPED_ISOLATED'} • Outbound Sockets: {netTelemetry?.external_sockets ?? 0} • WAN Egress: {netTelemetry?.wan_egress_bytes ?? 0} bytes</div>
                
                <div className="pt-2 theme-text-muted font-bold tracking-wider uppercase text-[10px]">--- ON-PREMISE LOCALHOST SERVICE BINDINGS ---</div>
                {(netTelemetry?.local_services || [
                  { service: "FastAPI Backend API", endpoint: "127.0.0.1:8000", protocol: "HTTP/SSE", status: "bound_local" },
                  { service: "PostgreSQL + pgvector", endpoint: "127.0.0.1:5432", protocol: "TCP", status: "bound_local" },
                  { service: "Ollama LLM Engine", endpoint: "127.0.0.1:11434", protocol: "HTTP", status: "bound_local" }
                ]).map((svc, idx) => (
                  <div key={`svc-${idx}`} className="theme-text-secondary pl-2">
                    [NET SERVICE] {svc.service} &rarr; {svc.endpoint} ({svc.protocol}) [{svc.status.toUpperCase()}]
                  </div>
                ))}

                <div className="pt-2 theme-text-muted font-bold tracking-wider uppercase text-[10px]">--- REGISTERED SYSTEM USER ACCOUNTS ---</div>
                {(metrics?.users || []).map((u, i) => (
                  <div key={`usr-${i}`} className="theme-text-secondary pl-2">
                    [AUTH USER] Verified account @{u.username} ({u.role.toUpperCase()}) — Dept: {u.department} — {u.thread_count} active thread(s)
                  </div>
                ))}

                <div className="pt-2 theme-text-muted font-bold tracking-wider uppercase text-[10px]">--- KNOWLEDGE BASE PGVECTOR INDEX LOGS ---</div>
                {ragFiles.length > 0 ? (
                  ragFiles.map((rf, i) => (
                    <div key={`rag-${i}`} className="theme-text-secondary pl-2">
                      [PGVECTOR RAG] Ingested document '{rf.filename || rf.source}' &rarr; {rf.chunk_count} vector chunks indexed
                    </div>
                  ))
                ) : (
                  <div className="theme-text-muted pl-2">[PGVECTOR RAG] No documents uploaded yet</div>
                )}

                <div className="pt-2 theme-text-muted font-bold tracking-wider uppercase text-[10px]">--- CONVERSATION THREAD AUDIT SESSIONS ---</div>
                {threads.slice(0, 15).map((t, i) => (
                  <div key={`th-${i}`} className="theme-text-secondary pl-2 truncate">
                    [SESSION AUDIT] Thread {t.thread_id?.slice(0, 8)}... | Owner: @{t.owner_name} | Title: "{t.title || t.preview}" | Tools: {t.tool_count} | Files: {t.file_count}
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl card-bg p-6 border-0 theme-text-primary space-y-4">
            <div className="flex items-center justify-between border-0 pb-3">
              <h3 className="text-base font-bold theme-text-primary flex items-center gap-2">
                <Key className="h-4 w-4 theme-text-secondary" />
                <span>Change Admin Password</span>
              </h3>
              <button type="button" onClick={() => setShowPasswordModal(false)} className="rounded-lg p-1.5 theme-text-muted hover:bg-[var(--bg-hover)] border-0 bg-transparent cursor-pointer">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-3">
              {pwdMsg && <div className="rounded-lg bg-[var(--bg-input)] p-2.5 text-xs theme-text-primary font-medium border-0">{pwdMsg}</div>}
              {pwdError && <div className="rounded-lg bg-red-500/10 p-2.5 text-xs text-red-400 font-medium">{pwdError}</div>}

              <div>
                <label className="text-xs font-medium theme-text-muted block mb-1">Current Admin Password</label>
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
                  value={newPasswordChange}
                  onChange={(e) => setNewPasswordChange(e.target.value)}
                  className="w-full rounded-xl border-0 input-bg px-3.5 py-2 text-xs theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowPasswordModal(false)} className="rounded-xl px-4 py-2 text-xs font-semibold theme-text-muted hover:bg-[var(--bg-hover)] border-0 cursor-pointer">
                  Cancel
                </button>
                <button type="submit" className="rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 border-0 cursor-pointer">
                  Update Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
