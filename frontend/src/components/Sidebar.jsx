import React, { useState, useRef, useEffect } from 'react';
import { 
  Plus, 
  PanelLeftClose, 
  Search, 
  BookOpen, 
  Sliders, 
  Trash2, 
  LogOut,
  Key,
  ShieldCheck,
  X,
  Check,
  AlertCircle,
  Sun,
  Moon,
  Edit2,
  User,
  ChevronDown
} from 'lucide-react';

export default function Sidebar({ 
  threads, 
  activeThreadId, 
  onSelectThread, 
  onNewThread,
  onDeleteThread,
  onRenameThread,
  onOpenKbModal,
  onOpenAdminModal,
  onOpen2faModal,
  currentUser,
  onLogout,
  isOpen,
  onToggleSidebar,
  theme = 'dark',
  onToggleTheme,
  token
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdStatus, setPwdStatus] = useState(null);
  const [isChangingPwd, setIsChangingPwd] = useState(false);

  const profileRef = useRef(null);
  const isAdmin = currentUser?.role === 'admin';

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
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

  const filteredThreads = threads.filter((t) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const previewStr = (t.title || t.preview || t.first_prompt || `Chat ${t.thread_id}`).toLowerCase();
    const ownerName = (t.user_name || '').toLowerCase();
    return previewStr.includes(term) || t.thread_id.toLowerCase().includes(term) || ownerName.includes(term);
  });

  if (!isOpen) return null;

  return (
    <aside className="flex h-full w-64 flex-col border-r sidebar-bg p-3 theme-text-primary transition-all duration-200 relative">
      {/* Sidebar Header */}
      <div className="flex items-center justify-between pb-2">
        <span className="text-sm font-semibold tracking-tight theme-text-primary flex items-center gap-1.5">
          Sovereign Agent
        </span>
        <button
          type="button"
          onClick={onToggleSidebar}
          className="flex h-7 w-7 items-center justify-center rounded-md theme-text-muted hover:bg-[var(--bg-hover)] hover:theme-text-primary transition-colors border-0 cursor-pointer"
          title="Close sidebar"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      {/* Logged-In User Profile Card with Dropdown Menu */}
      <div className="relative mb-3" ref={profileRef}>
        <button
          type="button"
          onClick={() => setShowProfileMenu((prev) => !prev)}
          className="w-full rounded-xl bg-[var(--bg-input)] px-3 py-2.5 flex items-center justify-between hover:bg-[var(--bg-hover)] transition-colors border-0 cursor-pointer text-left"
        >
          <div className="flex items-center gap-2.5 truncate">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-card)] theme-text-secondary border-0">
              <User className="h-4 w-4" />
            </div>
            <div className="truncate">
              <div className="font-semibold text-xs theme-text-primary truncate">
                {currentUser?.name || 'Authenticated User'}
              </div>
              <div className="text-[10px] theme-text-muted font-mono flex items-center gap-1.5 mt-0.5">
                <span>{currentUser?.department || 'Operations'}</span>
                <span className="rounded px-1.5 py-0.2 text-[9px] uppercase font-bold bg-[var(--bg-card)] theme-text-muted border-0">
                  {currentUser?.role || 'USER'}
                </span>
              </div>
            </div>
          </div>
          <ChevronDown className={`h-3.5 w-3.5 theme-text-muted transition-transform duration-200 ${showProfileMenu ? 'rotate-180' : ''}`} />
        </button>

        {/* Profile Popover Menu */}
        {showProfileMenu && (
          <div className="absolute left-0 right-0 top-full mt-1.5 z-50 rounded-xl card-bg p-1 border-0 space-y-0.5 animate-in fade-in zoom-in-95 duration-100">
            <button
              type="button"
              onClick={() => {
                setShowProfileMenu(false);
                setShowPasswordModal(true);
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
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
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
              >
                <ShieldCheck className="h-3.5 w-3.5 theme-text-secondary" />
                <span>2FA Security</span>
              </button>
            )}

            {onLogout && (
              <button
                type="button"
                onClick={() => {
                  setShowProfileMenu(false);
                  onLogout();
                }}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer border-0 pt-2"
              >
                <LogOut className="h-3.5 w-3.5 theme-text-secondary" />
                <span>Logout</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons: New Chat, Knowledge Base, Admin Panel */}
      <div className="mb-3 space-y-1.5">
        <button
          type="button"
          onClick={onNewThread}
          className="flex w-full items-center gap-2 rounded-lg card-bg py-2 px-3 text-xs font-medium theme-text-primary transition-colors hover:bg-[var(--bg-hover)] border-0 cursor-pointer"
        >
          <Plus className="h-4 w-4 theme-text-secondary" />
          <span>New chat</span>
        </button>

        {onOpenKbModal && (
          <button
            type="button"
            onClick={onOpenKbModal}
            className="flex w-full items-center gap-2 rounded-lg card-bg py-2 px-3 text-xs font-medium theme-text-primary transition-colors hover:bg-[var(--bg-hover)] border-0 cursor-pointer"
          >
            <BookOpen className="h-4 w-4 theme-text-secondary" />
            <span>Knowledge Base</span>
          </button>
        )}

        {isAdmin && onOpenAdminModal && (
          <button
            type="button"
            onClick={onOpenAdminModal}
            className="flex w-full items-center gap-2 rounded-lg card-bg py-2 px-3 text-xs font-medium theme-text-primary transition-colors hover:bg-[var(--bg-hover)] border-0 cursor-pointer"
          >
            <Sliders className="h-4 w-4 theme-text-secondary" />
            <span>Admin Dashboard</span>
          </button>
        )}
      </div>

      {/* Search Filter Bar */}
      <div className="relative mb-3">
        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 theme-text-muted" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search chats..."
          className="w-full rounded-lg border-0 input-bg py-1.5 pl-8 pr-3 text-xs theme-text-primary placeholder:theme-text-muted focus:outline-none transition-colors"
        />
      </div>

      {/* Thread List Header */}
      <div className="mb-1.5 flex items-center justify-between px-2 text-[11px] font-medium theme-text-muted">
        <span>{isAdmin ? 'All Conversations' : 'My Conversations'}</span>
        <span className="font-mono text-[10px]">{filteredThreads.length}</span>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-0.5">
        {filteredThreads.length === 0 ? (
          <div className="p-4 text-center text-xs theme-text-muted">
            {searchTerm ? "No matching chats found" : "No previous chats"}
          </div>
        ) : (
          filteredThreads.map((thread) => {
            const isActive = thread.thread_id === activeThreadId;
            const isEditing = editingThreadId === thread.thread_id;
            const titleText = thread.title || thread.preview || thread.first_prompt || `Chat ${thread.thread_id.slice(0, 8)}`;

            return (
              <div
                key={thread.thread_id}
                className={`group flex items-center justify-between rounded-lg py-1.5 px-2.5 text-xs transition-colors border-0 ${
                  isActive
                    ? 'bg-[var(--bg-hover)] theme-text-primary font-medium'
                    : 'theme-text-secondary hover:bg-[var(--bg-hover)] hover:theme-text-primary'
                }`}
              >
                {isEditing ? (
                  <div className="flex items-center gap-1 w-full">
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          if (onRenameThread) onRenameThread(thread.thread_id, editingTitle);
                          setEditingThreadId(null);
                        } else if (e.key === 'Escape') {
                          setEditingThreadId(null);
                        }
                      }}
                      autoFocus
                      className="flex-1 rounded border-0 bg-[var(--bg-input)] px-2 py-1 text-xs theme-text-primary focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (onRenameThread) onRenameThread(thread.thread_id, editingTitle);
                        setEditingThreadId(null);
                      }}
                      className="rounded p-1 theme-text-primary border-0 bg-transparent cursor-pointer"
                    >
                      <Check className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingThreadId(null)}
                      className="rounded p-1 theme-text-muted border-0 bg-transparent cursor-pointer"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onSelectThread(thread.thread_id)}
                      onDoubleClick={() => {
                        setEditingThreadId(thread.thread_id);
                        setEditingTitle(titleText);
                      }}
                      className="flex-1 text-left truncate border-0 bg-transparent cursor-pointer p-0"
                    >
                      <span className="truncate block">
                        {titleText}
                      </span>
                      {isAdmin && thread.user_name && (
                        <span className="text-[9px] font-mono theme-text-muted block truncate mt-0.5">
                          by {thread.user_name}
                        </span>
                      )}
                    </button>

                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                      {onRenameThread && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingThreadId(thread.thread_id);
                            setEditingTitle(titleText);
                          }}
                          className="rounded p-1 theme-text-muted hover:theme-text-primary transition-colors border-0 bg-transparent cursor-pointer"
                          title="Rename Chat"
                        >
                          <Edit2 className="h-3 w-3" />
                        </button>
                      )}

                      {isAdmin && onDeleteThread && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteThread(thread.thread_id);
                          }}
                          className="rounded p-1 theme-text-muted hover:theme-text-primary transition-colors border-0 bg-transparent cursor-pointer"
                          title="Delete Conversation"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Minimal Footer with Theme Toggle */}
      <div className="mt-2 border-0 pt-2 text-[11px] theme-text-muted px-1 flex justify-end items-center">
        {onToggleTheme && (
          <button
            type="button"
            onClick={onToggleTheme}
            className="flex h-7 w-7 items-center justify-center rounded-lg border-0 card-bg theme-text-primary hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4 theme-text-primary" />
            ) : (
              <Moon className="h-4 w-4 theme-text-primary" />
            )}
          </button>
        )}
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl card-bg p-6 border-0 theme-text-primary space-y-4">
            <div className="flex items-center justify-between border-0 pb-3">
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 theme-text-primary" />
                <h3 className="text-base font-bold theme-text-primary">
                  Change Your Password
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowPasswordModal(false);
                  setPwdStatus(null);
                }}
                className="rounded-lg p-1 theme-text-muted hover:bg-[var(--bg-hover)] transition-colors border-0 bg-transparent cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {pwdStatus && (
              <div className={`flex items-center gap-2 rounded-xl p-3 text-xs border-0 ${
                pwdStatus.type === 'success' ? 'bg-[var(--bg-input)] theme-text-primary' : 'bg-red-500/10 text-red-400'
              }`}>
                {pwdStatus.type === 'success' ? <Check className="h-4 w-4 shrink-0" /> : <AlertCircle className="h-4 w-4 shrink-0" />}
                <span>{pwdStatus.message}</span>
              </div>
            )}

            <form onSubmit={handleChangePasswordSubmit} className="space-y-3 font-sans">
              <div className="space-y-1">
                <label className="text-xs font-semibold theme-text-primary">Current Password</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="Enter current password"
                  className="w-full rounded-xl border-0 input-bg py-2 px-3 text-sm theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold theme-text-primary">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="w-full rounded-xl border-0 input-bg py-2 px-3 text-sm theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold theme-text-primary">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  className="w-full rounded-xl border-0 input-bg py-2 px-3 text-sm theme-text-primary focus:outline-none"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  className="rounded-lg card-bg theme-text-muted px-4 py-2 text-xs font-medium hover:theme-text-primary transition-all border-0 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isChangingPwd}
                  className="rounded-lg bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] px-4 py-2 text-xs font-semibold hover:opacity-90 transition-all border-0 cursor-pointer disabled:opacity-50"
                >
                  {isChangingPwd ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </aside>
  );
}
