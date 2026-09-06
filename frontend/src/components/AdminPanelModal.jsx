import React, { useState, useEffect } from 'react';
import { ShieldCheck, Users, HardDrive, Database, X, Lock, CheckCircle2, UserPlus, AlertCircle } from 'lucide-react';

export default function AdminPanelModal({ isOpen, onClose, token }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // New user form state
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('user');
  const [newDepartment, setNewDepartment] = useState('Refinery Operations');
  const [createMsg, setCreateMsg] = useState(null);
  const [createError, setCreateError] = useState(null);

  const fetchAdminMetrics = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/admin/audit', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error('Error fetching admin metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && token) {
      fetchAdminMetrics();
    }
  }, [isOpen, token]);

  const handleCreateUserSubmit = async (e) => {
    e.preventDefault();
    if (!newUsername.trim() || !newPassword.trim() || !newName.trim() || !token) return;

    setCreateMsg(null);
    setCreateError(null);

    try {
      const res = await fetch('http://localhost:8000/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          username: newUsername,
          password: newPassword,
          name: newName,
          role: newRole,
          department: newDepartment
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create user account');
      }

      setCreateMsg(`Account for '${data.name}' (@${data.username}) created successfully!`);
      setNewUsername('');
      setNewPassword('');
      setNewName('');
      await fetchAdminMetrics();
    } catch (err) {
      setCreateError(err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-3xl rounded-2xl card-bg p-6 shadow-2xl border-0 theme-text-primary space-y-5 max-h-[88vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[var(--border-muted)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20 text-blue-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold theme-text-primary">
                Enterprise Admin & Governance Dashboard
              </h3>
              <div className="text-[11px] theme-text-muted">
                Role-Based Access Control (RBAC) & Sovereign Server Governance
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 theme-text-muted hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs theme-text-muted font-mono">
            Loading enterprise audit telemetry...
          </div>
        ) : (
          <div className="space-y-4 overflow-y-auto pr-1">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl bg-[var(--bg-input)] p-3 shadow-sm border-0">
                <div className="flex items-center justify-between text-xs theme-text-muted mb-1">
                  <span>Users</span>
                  <Users className="h-3.5 w-3.5 text-blue-400" />
                </div>
                <div className="text-xl font-bold font-mono theme-text-primary">
                  {metrics?.total_users || 0}
                </div>
                <div className="text-[10px] theme-text-muted mt-0.5">SQLite RBAC User DB</div>
              </div>

              <div className="rounded-xl bg-[var(--bg-input)] p-3 shadow-sm border-0">
                <div className="flex items-center justify-between text-xs theme-text-muted mb-1">
                  <span>Conversations</span>
                  <Database className="h-3.5 w-3.5 text-emerald-400" />
                </div>
                <div className="text-xl font-bold font-mono theme-text-primary">
                  {metrics?.total_threads || 0}
                </div>
                <div className="text-[10px] theme-text-muted mt-0.5">SQLite Checkpoint DB</div>
              </div>

              <div className="rounded-xl bg-[var(--bg-input)] p-3 shadow-sm border-0">
                <div className="flex items-center justify-between text-xs theme-text-muted mb-1">
                  <span>Workspace Storage</span>
                  <HardDrive className="h-3.5 w-3.5 text-amber-400" />
                </div>
                <div className="text-xl font-bold font-mono theme-text-primary">
                  {metrics?.workspace_storage_mb || 0} MB
                </div>
                <div className="text-[10px] theme-text-muted mt-0.5">{metrics?.workspace_files_count || 0} files staged</div>
              </div>

              <div className="rounded-xl bg-[var(--bg-input)] p-3 shadow-sm border-0">
                <div className="flex items-center justify-between text-xs theme-text-muted mb-1">
                  <span>RAG Vector DB</span>
                  <Lock className="h-3.5 w-3.5 text-purple-400" />
                </div>
                <div className="text-xl font-bold font-mono theme-text-primary">
                  {metrics?.rag_kb_documents || 0} Docs
                </div>
                <div className="text-[10px] theme-text-muted mt-0.5">{metrics?.rag_kb_chunks || 0} vector chunks</div>
              </div>
            </div>

            {/* User Roster Table & Create User Header */}
            <div className="rounded-xl bg-[var(--bg-input)] p-4 shadow-sm border-0 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold theme-text-primary">
                <span>Enterprise User Roster & RBAC Roles</span>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(!showCreateForm)}
                  className="flex items-center gap-1 rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-2.5 py-1 text-[11px] font-medium hover:opacity-90 transition-all border-0 cursor-pointer"
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  <span>{showCreateForm ? "Close Form" : "Create User Account"}</span>
                </button>
              </div>

              {/* Create New User Account Form */}
              {showCreateForm && (
                <form onSubmit={handleCreateUserSubmit} className="rounded-xl card-bg p-3.5 space-y-3 border-0">
                  <div className="text-xs font-bold theme-text-primary flex items-center gap-1.5">
                    <UserPlus className="h-4 w-4 text-blue-400" />
                    <span>Register New Enterprise User Account</span>
                  </div>

                  {createMsg && (
                    <div className="rounded-lg bg-emerald-500/10 p-2 text-[11px] text-emerald-400 font-medium">
                      {createMsg}
                    </div>
                  )}

                  {createError && (
                    <div className="rounded-lg bg-red-500/10 p-2 text-[11px] text-red-400 font-medium flex items-center gap-1">
                      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                      <span>{createError}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div>
                      <label className="text-[10px] font-medium theme-text-muted">Full Name</label>
                      <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="e.g. Ramesh Kumar"
                        className="w-full rounded-lg border-0 input-bg px-2.5 py-1.5 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-[10px] font-medium theme-text-muted">Username</label>
                      <input
                        type="text"
                        value={newUsername}
                        onChange={(e) => setNewUsername(e.target.value)}
                        placeholder="e.g. ramesh1"
                        className="w-full rounded-lg border-0 input-bg px-2.5 py-1.5 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-[10px] font-medium theme-text-muted">Initial Password</label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full rounded-lg border-0 input-bg px-2.5 py-1.5 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-[10px] font-medium theme-text-muted">Department</label>
                      <input
                        type="text"
                        value={newDepartment}
                        onChange={(e) => setNewDepartment(e.target.value)}
                        placeholder="e.g. Thermal Maintenance"
                        className="w-full rounded-lg border-0 input-bg px-2.5 py-1.5 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] theme-text-muted">Role:</span>
                      <select
                        value={newRole}
                        onChange={(e) => setNewRole(e.target.value)}
                        className="rounded-lg border-0 input-bg px-2 py-1 text-xs theme-text-primary focus:outline-none"
                      >
                        <option value="user">User (Standard Access)</option>
                        <option value="admin">Admin (System Governance)</option>
                      </select>
                    </div>

                    <button
                      type="submit"
                      className="rounded-lg bg-blue-600 text-white px-3 py-1.5 text-xs font-semibold hover:bg-blue-500 transition-colors border-0 cursor-pointer"
                    >
                      Save & Register User
                    </button>
                  </div>
                </form>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border-muted)] text-[11px] theme-text-muted">
                      <th className="py-2 px-2 font-medium">User Profile</th>
                      <th className="py-2 px-2 font-medium">Department</th>
                      <th className="py-2 px-2 font-medium">RBAC Role</th>
                      <th className="py-2 px-2 font-medium text-right">Threads</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(metrics?.users || []).map((u) => (
                      <tr key={u.user_id} className="border-b border-[var(--border-muted)]/50 hover:bg-[var(--bg-hover)] transition-colors">
                        <td className="py-2.5 px-2 font-medium theme-text-primary">
                          <div className="flex items-center gap-2">
                            <span className={`h-2.5 w-2.5 rounded-full ${u.avatar_color || 'bg-gray-400'}`}></span>
                            <div>
                              <div className="font-semibold">{u.name}</div>
                              <div className="text-[10px] theme-text-muted font-mono">@{u.username}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-2.5 px-2 theme-text-muted text-[11px]">
                          {u.department}
                        </td>
                        <td className="py-2.5 px-2">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-mono text-[10px] font-semibold ${
                            u.role === 'admin' 
                              ? 'bg-blue-500/15 text-blue-400' 
                              : 'bg-emerald-500/15 text-emerald-400'
                          }`}>
                            {u.role === 'admin' ? <ShieldCheck className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
                            {u.role.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-right font-mono font-medium theme-text-primary">
                          {u.thread_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Admin Policy Summary */}
            <div className="rounded-xl card-bg p-3.5 text-xs theme-text-muted leading-relaxed font-sans border-0">
              <strong className="theme-text-primary font-semibold">RBAC Governance Rules:</strong>
              <ul className="list-disc pl-4 mt-1 space-y-1 text-[11px]">
                <li>Standard <strong>User</strong> accounts can only view and manage their own conversation threads.</li>
                <li><strong>Admin</strong> accounts possess system-wide auditing visibility across all threads, workspace storage, and Knowledge Base ingestion operations.</li>
                <li>All user passwords are securely hashed via PBKDF2-SHA256 and stored locally in <code>workbench_checkpoints.db</code>.</li>
              </ul>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="flex justify-end pt-2 border-t border-[var(--border-muted)]">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 transition-all border-0 cursor-pointer"
          >
            Close Admin Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
