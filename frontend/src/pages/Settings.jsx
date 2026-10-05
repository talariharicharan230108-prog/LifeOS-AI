import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  User,
  Clock,
  Key,
  Download,
  Trash2,
  CheckCircle,
  AlertTriangle,
  Moon,
  Sun,
  ShieldCheck,
  RefreshCw,
  Lock,
  LogOut
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { normalizeWorkingDays } from '../utils/constants';
import { useAuth } from '../context/AuthContext';
import * as api from '../services/api';
import Modal from '../components/Modal';

export default function Settings() {
  const {
    data,
    updateUserProfile,
    updateRoutine,
    updateWorkingDays,
    theme,
    toggleTheme,
    resetAll,
    geminiInfo,
    setGeminiInfo
  } = useApp();

  const { user: authUser, logout, changePassword, updateProfile } = useAuth();

  // Profile form
  const [name, setName] = useState(authUser?.name || data?.user?.name || '');
  const [college, setCollege] = useState(data?.user?.college || '');
  const [course, setCourse] = useState(data?.user?.course || '');
  const [profileSaved, setProfileSaved] = useState(false);

  // Password Change Form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordStatusMsg, setPasswordStatusMsg] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Routine form
  const [wakeTime, setWakeTime] = useState(data?.routine?.wakeTime || '07:00');
  const [sleepTime, setSleepTime] = useState(data?.routine?.sleepTime || '23:00');
  const [collegeStart, setCollegeStart] = useState(data?.routine?.collegeStart || '09:00');
  const [collegeEnd, setCollegeEnd] = useState(data?.routine?.collegeEnd || '16:00');
  const [studyHours, setStudyHours] = useState(data?.routine?.studyHours || 3);
  const [routineSaved, setRoutineSaved] = useState(false);

  // Working Days form
  const [workingDays, setWorkingDays] = useState(
    normalizeWorkingDays(data?.settings?.workingDays)
  );
  const [workingDaysSaved, setWorkingDaysSaved] = useState(false);

  React.useEffect(() => {
    setWorkingDays(normalizeWorkingDays(data?.settings?.workingDays));
  }, [data?.settings?.workingDays]);

  // API Key state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [keyTesting, setKeyTesting] = useState(false);
  const [aiTestResult, setAiTestResult] = useState('');

  // Clear data confirmation modal
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (name.trim()) {
      try {
        await updateProfile({ name: name.trim() });
      } catch (err) {
        console.warn('Profile update error:', err);
      }
    }
    updateUserProfile({ name: name.trim(), college: college.trim(), course: course.trim() });
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2500);
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordStatusMsg('');

    if (!currentPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }
    if (!newPassword || newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }

    setPasswordLoading(true);
    try {
      const res = await changePassword({
        currentPassword,
        newPassword,
        confirmNewPassword,
      });
      setPasswordStatusMsg(res?.message || 'Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (err) {
      setPasswordError(err.message || 'Failed to change password.');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to log out of LifeOS?')) {
      await logout();
    }
  };

  const handleSaveRoutine = (e) => {
    e.preventDefault();
    updateRoutine({
      wakeTime,
      sleepTime,
      collegeStart,
      collegeEnd,
      studyHours: Number(studyHours),
    });
    setRoutineSaved(true);
    setTimeout(() => setRoutineSaved(false), 2000);
  };

  const handleSaveWorkingDays = async (e) => {
    e.preventDefault();
    try {
      if (typeof updateWorkingDays === 'function') {
        await updateWorkingDays(workingDays);
      }
      setWorkingDaysSaved(true);
      setTimeout(() => setWorkingDaysSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save working days in Settings:', err);
      alert('Failed to save working days. Please try again.');
    }
  };

  const toggleDay = (day) => {
    if (workingDays.includes(day)) {
      if (workingDays.length === 1) return;
      setWorkingDays(workingDays.filter((d) => d !== day));
    } else {
      setWorkingDays([...workingDays, day]);
    }
  };

  const handleTestAiConnection = async () => {
    setKeyTesting(true);
    setAiTestResult('Testing connection...');
    try {
      const res = await api.testAIConnection();
      setAiTestResult(res?.message || (res?.connected ? 'AI connection successful.' : 'AI connection failed.'));
      const statusRes = await api.fetchAIStatus();
      if (statusRes) setGeminiInfo(statusRes);
    } catch (err) {
      setAiTestResult('AI connection failed.');
    } finally {
      setKeyTesting(false);
    }
  };

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    try {
      setKeyTesting(true);
      setAiTestResult('Saving and validating API key with Google Gemini...');
      const res = await api.updateApiKey(apiKeyInput.trim());
      setAiTestResult(res?.message || 'API key saved successfully.');
      setApiKeyInput('');
      const statusRes = await api.fetchAIStatus();
      if (statusRes) setGeminiInfo(statusRes);
    } catch (err) {
      setAiTestResult('AI connection failed.');
    } finally {
      setKeyTesting(false);
    }
  };

  const handleExportData = () => {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lifeos_backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleConfirmReset = () => {
    resetAll();
    setIsResetModalOpen(false);
  };

  const displayEmail = authUser?.email || data?.email || 'user@lifeos.app';

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header bar */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-indigo-600" />
            Account & System Settings
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage your personal profile, credentials, planning constraints, and AI connection.
          </p>
        </div>

        <button
          onClick={handleLogout}
          id="settings-logout-btn"
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200/60 dark:border-rose-900/60 text-rose-600 dark:text-rose-400 hover:bg-rose-100 font-semibold text-xs transition cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SECTION 1: Account & Profile */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <User className="w-4 h-4 text-indigo-600" />
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Account Profile
            </h3>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Full Name
              </label>
              <input
                id="profile-name-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Account Email (read-only)
              </label>
              <input
                type="email"
                disabled
                value={displayEmail}
                className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-500 dark:text-slate-400 cursor-not-allowed"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  College / University
                </label>
                <input
                  type="text"
                  value={college}
                  onChange={(e) => setCollege(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Course
                </label>
                <input
                  type="text"
                  value={course}
                  onChange={(e) => setCourse(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              {profileSaved && (
                <span className="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1 font-semibold">
                  <CheckCircle className="w-3.5 h-3.5" /> Profile updated!
                </span>
              )}
              <button
                type="submit"
                id="save-profile-btn"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold ml-auto cursor-pointer"
              >
                Save Profile
              </button>
            </div>
          </form>
        </div>

        {/* SECTION 2: Change Password */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <Lock className="w-4 h-4 text-indigo-600" />
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Change Password
            </h3>
          </div>

          <form onSubmit={handleChangePassword} className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Current Password
              </label>
              <input
                id="current-password-input"
                type="password"
                required
                placeholder="••••••••"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                New Password (minimum 8 characters)
              </label>
              <input
                id="new-password-input"
                type="password"
                required
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Confirm New Password
              </label>
              <input
                id="confirm-new-password-input"
                type="password"
                required
                placeholder="••••••••"
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>

            {passwordError && (
              <p className="text-xs text-rose-500 font-semibold">{passwordError}</p>
            )}
            {passwordStatusMsg && (
              <p className="text-xs text-emerald-500 font-semibold flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> {passwordStatusMsg}
              </p>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                id="change-password-btn"
                disabled={passwordLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold disabled:opacity-50 cursor-pointer"
              >
                {passwordLoading ? 'Updating Password...' : 'Change Password'}
              </button>
            </div>
          </form>
        </div>

        {/* SECTION 3: AI Assistant & Connection */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-indigo-600" />
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
                AI Assistant Connection
              </h3>
            </div>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                (geminiInfo?.connected || geminiInfo?.ok)
                  ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                  : 'bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300'
              }`}
            >
              {(geminiInfo?.connected || geminiInfo?.ok) ? 'AI Connected' : 'Checking Connection'}
            </span>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/60 text-xs">
            <div>
              <span className="font-semibold text-slate-800 dark:text-slate-200">Google Gemini AI Engine</span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Multi-model automatic fallback enabled silently.
              </p>
            </div>
            <button
              type="button"
              id="test-ai-connection-btn"
              onClick={handleTestAiConnection}
              disabled={keyTesting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 font-semibold text-[11px] transition active:scale-95 disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3 h-3 ${keyTesting ? 'animate-spin' : ''}`} />
              Test AI Connection
            </button>
          </div>

          {aiTestResult && (
            <p className={`text-xs font-semibold ${aiTestResult.includes('successful') ? 'text-emerald-500' : aiTestResult.includes('failed') ? 'text-rose-500' : 'text-indigo-400'}`}>
              {aiTestResult}
            </p>
          )}

          <form onSubmit={handleSaveApiKey} className="space-y-3 text-xs pt-2">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Update Gemini API Key (stored safely in backend)
              </label>
              <input
                type="password"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Paste key to update..."
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!apiKeyInput.trim() || keyTesting}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 active:scale-95 disabled:opacity-50 cursor-pointer"
              >
                {keyTesting ? 'Saving & Verifying...' : 'Save & Verify Key'}
              </button>
            </div>
          </form>
        </div>

        {/* SECTION 4: Daily Routine Constraints */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <Clock className="w-4 h-4 text-indigo-600" />
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Daily Routine Constraints
            </h3>
          </div>

          <form onSubmit={handleSaveRoutine} className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Wake-Up Time
                </label>
                <input
                  type="time"
                  value={wakeTime}
                  onChange={(e) => setWakeTime(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Sleep Time
                </label>
                <input
                  type="time"
                  value={sleepTime}
                  onChange={(e) => setSleepTime(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  College Start
                </label>
                <input
                  type="time"
                  value={collegeStart}
                  onChange={(e) => setCollegeStart(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  College End
                </label>
                <input
                  type="time"
                  value={collegeEnd}
                  onChange={(e) => setCollegeEnd(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Target Study Hours / Day
              </label>
              <input
                type="number"
                min="1"
                max="12"
                value={studyHours}
                onChange={(e) => setStudyHours(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              {routineSaved && (
                <span className="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1 font-semibold">
                  <CheckCircle className="w-3.5 h-3.5" /> Routine saved!
                </span>
              )}
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold ml-auto cursor-pointer"
              >
                Save Routine
              </button>
            </div>
          </form>
        </div>

        {/* SECTION 5: Working Days */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <Clock className="w-4 h-4 text-amber-500" />
            <div>
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
                Working Days Configuration
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Unselected days are treated as non-working days by the AI planner.
              </p>
            </div>
          </div>

          <form onSubmit={handleSaveWorkingDays} className="space-y-3 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => {
                const isSelected = workingDays.includes(day);
                return (
                  <button
                    key={day}
                    type="button"
                    onClick={() => toggleDay(day)}
                    className={`p-2.5 rounded-xl border text-left transition flex items-center justify-between cursor-pointer ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/60 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-bold'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-500 hover:border-slate-300'
                    }`}
                  >
                    <span>{day}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                      isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                    }`}>
                      {isSelected ? 'Active' : 'Off'}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-between pt-2">
              {workingDaysSaved && (
                <span className="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1 font-semibold">
                  <CheckCircle className="w-3.5 h-3.5" /> Working days updated!
                </span>
              )}
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold ml-auto cursor-pointer"
              >
                Save Working Days
              </button>
            </div>
          </form>
        </div>

        {/* SECTION 6: Data & Theme */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <ShieldCheck className="w-4 h-4 text-indigo-600" />
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Data & Theme
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            {/* Theme Toggle */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div>
                <p className="font-semibold text-slate-800 dark:text-slate-200">Interface Theme</p>
                <p className="text-[11px] text-slate-400">Current: {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</p>
              </div>
              <button
                onClick={toggleTheme}
                className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 font-semibold cursor-pointer"
              >
                Toggle Theme
              </button>
            </div>

            {/* Export */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div>
                <p className="font-semibold text-slate-800 dark:text-slate-200">Export LifeOS Data</p>
                <p className="text-[11px] text-slate-400">Download complete JSON backup file</p>
              </div>
              <button
                onClick={handleExportData}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 font-semibold cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" /> Export
              </button>
            </div>

            {/* Reset */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200/50 dark:border-rose-900/50">
              <div>
                <p className="font-semibold text-rose-800 dark:text-rose-200">Clear All Stored Data</p>
                <p className="text-[11px] text-rose-500">Resets tasks, calendar events, documents, and profile</p>
              </div>
              <button
                onClick={() => setIsResetModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold cursor-pointer"
              >
                Reset LifeOS
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal for Reset */}
      <Modal
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        title="Confirm Reset LifeOS"
      >
        <div className="space-y-4 text-xs">
          <p className="text-slate-600 dark:text-slate-300">
            Are you sure you want to clear all data? This will permanently delete your stored tasks, subjects, schedule events, and uploaded documents.
          </p>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setIsResetModalOpen(false)}
              className="px-4 py-2 rounded-xl text-slate-500 hover:text-slate-700 cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmReset}
              className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-xl cursor-pointer"
            >
              Yes, Reset Everything
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
