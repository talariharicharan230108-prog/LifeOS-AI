import React, { createContext, useContext, useState, useEffect } from 'react';
import * as api from '../services/api';
import { useAuth } from './AuthContext';

import { DEFAULT_WORKING_DAYS, normalizeWorkingDays } from '../utils/constants';

const AppContext = createContext(null);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const { user: authUser } = useAuth();
  const [data, setData] = useState({
    user: null,
    routine: {
      wakeTime: '07:00',
      sleepTime: '23:00',
      collegeStart: '09:00',
      collegeEnd: '16:00',
      studyHours: 3,
      breakPreference: '15 mins per 45 mins',
      preferredSubjects: [],
    },
    settings: {
      onboardingCompleted: false,
      workingDays: DEFAULT_WORKING_DAYS,
    },
    tasks: [],
    subjects: [],
    events: [],
    goals: [],
    documents: [],
    activity: [],
    holidays: [],
  });

  const [activeTab, setActiveTab] = useState('dashboard');
  const [theme, setTheme] = useState(() => localStorage.getItem('lifeos_theme') || 'dark');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [dataOwnerId, setDataOwnerId] = useState(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [geminiInfo, setGeminiInfo] = useState({ configured: false });

  // Initialize theme
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('lifeos_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const loadDocuments = async () => {
    try {
      const docRes = await api.fetchDocuments();
      const docs = docRes?.documents || [];
      setData((prev) => ({ ...prev, documents: docs }));
      return docs;
    } catch (err) {
      console.warn('Failed to load documents:', err);
      return [];
    }
  };

  // Load data from backend — always fetches per-user data including holidays
  const refreshData = async () => {
    if (!authUser?.id) {
      setLoading(false);
      return;
    }

    const currentUserId = String(authUser.id);

    try {
      setLoading(true);
      setDataLoaded(false);

      // Only start with a clean state when actually switching accounts.
      if (dataOwnerId !== currentUserId) {
        setData({
          user: null,
          routine: {
            wakeTime: '07:00',
            sleepTime: '23:00',
            collegeStart: '09:00',
            collegeEnd: '16:00',
            studyHours: 3,
            breakPreference: '15 mins per 45 mins',
            preferredSubjects: []
          },
          settings: {
            onboardingCompleted: false,
            workingDays: DEFAULT_WORKING_DAYS
          },
          tasks: [],
          subjects: [],
          events: [],
          goals: [],
          documents: [],
          activity: [],
          holidays: []
        });
        setDataOwnerId(currentUserId);
      }

      const res = await api.fetchAllData();

      if (res && typeof res === 'object' && !res.detail) {
        setData({
          user: res.user ? { ...res.user } : null,

          routine: res.routine || {
            wakeTime: '07:00',
            sleepTime: '23:00',
            collegeStart: '09:00',
            collegeEnd: '16:00',
            studyHours: 3,
            breakPreference: '15 mins per 45 mins',
            preferredSubjects: [],
          },

          settings: {
            onboardingCompleted: false,
            workingDays: DEFAULT_WORKING_DAYS,
            ...(res.settings || {}),
            onboardingCompleted: res.settings?.onboardingCompleted === true,
            workingDays: normalizeWorkingDays(res.settings?.workingDays || DEFAULT_WORKING_DAYS)
          },

          tasks: Array.isArray(res.tasks) ? res.tasks : [],
          subjects: Array.isArray(res.subjects) ? res.subjects : [],
          events: Array.isArray(res.events) ? res.events : [],
          goals: Array.isArray(res.goals) ? res.goals : [],
          documents: Array.isArray(res.documents) ? res.documents : [],
          activity: Array.isArray(res.activity) ? res.activity : [],

          // NEVER inherit holidays from another account.
          holidays: Array.isArray(res.holidays) ? res.holidays : [],
        });

        setBackendOnline(true);
        setDataLoaded(true);
      } else {
        // Backend unavailable: only use THIS user's backup.
        const backupKey = `lifeos_local_backup_${currentUserId}`;
        const local = localStorage.getItem(backupKey);

        if (local) {
          try {
            const parsed = JSON.parse(local);

            setData({
              user: parsed.user || null,
              routine: parsed.routine || {
                wakeTime: '07:00',
                sleepTime: '23:00',
                collegeStart: '09:00',
                collegeEnd: '16:00',
                studyHours: 3,
                breakPreference: '15 mins per 45 mins',
                preferredSubjects: [],
              },
              settings: {
                onboardingCompleted: false,
                workingDays: DEFAULT_WORKING_DAYS,
                ...(parsed.settings || {}),
                onboardingCompleted: parsed.settings?.onboardingCompleted === true,
                workingDays: normalizeWorkingDays(parsed.settings?.workingDays || DEFAULT_WORKING_DAYS)
              },
              tasks: Array.isArray(parsed.tasks) ? parsed.tasks : [],
              subjects: Array.isArray(parsed.subjects) ? parsed.subjects : [],
              events: Array.isArray(parsed.events) ? parsed.events : [],
              goals: Array.isArray(parsed.goals) ? parsed.goals : [],
              documents: Array.isArray(parsed.documents) ? parsed.documents : [],
              activity: Array.isArray(parsed.activity) ? parsed.activity : [],
              holidays: Array.isArray(parsed.holidays) ? parsed.holidays : [],
            });
            setDataLoaded(true);
          } catch (err) {
            console.error('Invalid account backup:', err);
          }
        }

        setBackendOnline(false);
      }

      await loadDocuments();

      const aiStatus = await api.fetchAIStatus().catch(() => null);

      if (aiStatus) {
        setGeminiInfo(aiStatus);
      }

    } catch (err) {
      console.error('Failed to load account data:', err);
      setBackendOnline(false);

      // Only fallback to the CURRENT user's backup.
      const backupKey = `lifeos_local_backup_${currentUserId}`;
      const local = localStorage.getItem(backupKey);

      if (local) {
        try {
          const parsed = JSON.parse(local);

          const defaultSettings = {
            onboardingCompleted: false,
            workingDays: DEFAULT_WORKING_DAYS
          };
          const fallbackSettings = parsed.settings || {};

          setData({
            ...parsed,
            user: parsed.user ? { ...parsed.user } : null,
            holidays: Array.isArray(parsed.holidays) ? parsed.holidays : [],
            settings: {
              ...defaultSettings,
              ...fallbackSettings,
              onboardingCompleted: fallbackSettings.onboardingCompleted === true,
              workingDays: normalizeWorkingDays(fallbackSettings.workingDays)
            }
          });
        } catch (e) {
          console.error('Failed to load account backup:', e);
        }
      }
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    if (!authUser?.id) {
      setDataOwnerId(null);

      setData({
        user: null,
        routine: {
          wakeTime: '07:00',
          sleepTime: '23:00',
          collegeStart: '09:00',
          collegeEnd: '16:00',
          studyHours: 3,
          breakPreference: '15 mins per 45 mins',
          preferredSubjects: [],
        },
        settings: {
          onboardingCompleted: false,
          workingDays: DEFAULT_WORKING_DAYS,
        },
        tasks: [],
        subjects: [],
        events: [],
        goals: [],
        documents: [],
        activity: [],
        holidays: [],
      });

      return;
    }

    refreshData();
  }, [authUser?.id]);

  // Save backup to localStorage on update, isolated strictly per authenticated user
  useEffect(() => {
    if (!authUser?.id) return;

    const currentUserId = String(authUser.id);

    // Never save until the real account data has finished loading.
    if (!dataLoaded) return;

    // Never save data belonging to another account.
    if (!dataOwnerId || dataOwnerId !== currentUserId) {
      return;
    }

    if (!data?.user) {
      return;
    }

    localStorage.setItem(
      `lifeos_local_backup_${currentUserId}`,
      JSON.stringify(data)
    );
  }, [data, authUser?.id, dataOwnerId, dataLoaded]);

  // Derived real notifications based on user data
  const notifications = React.useMemo(() => {
    const list = [];
    const today = new Date().toISOString().split('T')[0];

    // 1. Task deadlines
    (data.tasks || []).forEach((t) => {
      if (!t.completed && t.deadline) {
        if (t.deadline === today) {
          list.push({
            id: `task-today-${t.id}`,
            title: 'Task Due Today',
            message: `"${t.title}" is due today!`,
            type: 'critical',
            tab: 'tasks',
          });
        } else if (t.deadline < today) {
          list.push({
            id: `task-overdue-${t.id}`,
            title: 'Task Overdue',
            message: `"${t.title}" deadline has passed.`,
            type: 'critical',
            tab: 'tasks',
          });
        } else if (t.priority === 'high') {
          list.push({
            id: `task-high-${t.id}`,
            title: 'High Priority Task',
            message: `"${t.title}" needs attention.`,
            type: 'warning',
            tab: 'tasks',
          });
        }
      }
    });

    // 2. Exam dates
    (data.subjects || []).forEach((s) => {
      if (s.examDate) {
        const diff = Math.ceil((new Date(s.examDate) - new Date()) / (1000 * 60 * 60 * 24));
        if (diff >= 0 && diff <= 7) {
          list.push({
            id: `exam-${s.id}`,
            title: 'Upcoming Exam',
            message: `${s.name} exam in ${diff} day(s)!`,
            type: 'warning',
            tab: 'academic',
          });
        }
      }
    });

    // 3. Goal progress
    (data.goals || []).forEach((g) => {
      if (g.progress < 25 && g.deadline) {
        list.push({
          id: `goal-${g.id}`,
          title: 'Goal Reminder',
          message: `Check your progress on "${g.title}".`,
          type: 'info',
          tab: 'goals',
        });
      }
    });

    return list;
  }, [data]);

  // CRUD Helper Handlers
  const handleOnboardingComplete = async (userData, routineData, initialSubjects) => {
    try {
      // 1. Prepare data
      const updatedProfile = {
        name: userData.name,
        academic_institution: userData.college,
        degree_program: userData.course,
        wake_time: routineData.wakeTime,
        sleep_time: routineData.sleepTime,
        college_start: routineData.collegeStart,
        college_end: routineData.collegeEnd,
        daily_study_hours: routineData.studyHours,
      };

      // 2. Save profile to backend (this sets onboardingCompleted=True in main.py)
      await api.saveUserProfile(updatedProfile);

      // Instantly update the UI so the modal disappears without waiting for full refresh
      setData((prev) => ({
        ...prev,
        settings: {
          ...prev.settings,
          onboardingCompleted: true
        }
      }));

      // 3. Save initial subjects if provided
      if (initialSubjects && initialSubjects.length > 0) {
        for (const sub of initialSubjects) {
          await api.createSubject(sub).catch(() => null);
        }
      }

      // 4. Reload data from backend to ensure state is absolutely in sync
      refreshData();
    } catch (e) {
      console.error('Error completing onboarding:', e);
      alert('Failed to save onboarding data. Please try again.');
    }
  };

  const addTask = async (task) => {
    try {
      const res = await api.createTask(task);
      const created = res?.task || res;
      if (created && created.id !== undefined) {
        setData((prev) => ({
          ...prev,
          tasks: [...prev.tasks.filter((t) => t.id !== created.id), created],
        }));
      }
    } catch (e) {
      const newTask = { ...task, id: Math.random().toString(36).substr(2, 8), completed: false };
      setData((prev) => ({ ...prev, tasks: [...prev.tasks, newTask] }));
    }
  };

  const updateTask = async (id, updates) => {
    try {
      await api.updateTask(id, updates);
      setData((prev) => ({
        ...prev,
        tasks: prev.tasks.map((t) => (t.id === id ? { ...t, ...updates } : t)),
      }));
    } catch (e) {
      setData((prev) => ({
        ...prev,
        tasks: prev.tasks.map((t) => (t.id === id ? { ...t, ...updates } : t)),
      }));
    }
  };

  const deleteTask = async (id) => {
    try {
      await api.deleteTask(id);
    } catch (e) { }
    setData((prev) => ({ ...prev, tasks: prev.tasks.filter((t) => t.id !== id) }));
  };

  const addEvent = async (event) => {
    try {
      const res = await api.createEvent(event);
      const created = res?.events || (res?.event ? [res.event] : (res?.id ? [res] : []));
      if (Array.isArray(created) && created.length > 0) {
        setData((prev) => ({ ...prev, events: [...prev.events, ...created] }));
      }
    } catch (e) {
      const newEv = { ...event, id: Math.random().toString(36).substr(2, 8) };
      setData((prev) => ({ ...prev, events: [...prev.events, newEv] }));
    }
  };

  const updateEvent = async (id, updates) => {
    try {
      await api.updateEvent(id, updates);
    } catch (e) { }
    setData((prev) => ({
      ...prev,
      events: prev.events.map((e) => (e.id === id ? { ...e, ...updates } : e)),
    }));
  };

  const deleteEvent = async (id) => {
    try {
      await api.deleteEvent(id);
    } catch (e) { }
    setData((prev) => ({ ...prev, events: prev.events.filter((e) => e.id !== id) }));
  };

  const addSubject = async (sub) => {
    try {
      const res = await api.createSubject(sub);
      const created = res?.subject || res;
      if (created && created.id !== undefined) {
        setData((prev) => ({
          ...prev,
          subjects: [...prev.subjects.filter((s) => s.id !== created.id), created],
        }));
      }
    } catch (e) {
      const newSub = { ...sub, id: Math.random().toString(36).substr(2, 8) };
      setData((prev) => ({ ...prev, subjects: [...prev.subjects, newSub] }));
    }
  };

  const updateSubject = async (id, updates) => {
    try {
      await api.updateSubject(id, updates);
    } catch (e) { }
    setData((prev) => ({
      ...prev,
      subjects: prev.subjects.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    }));
  };

  const deleteSubject = async (id) => {
    try {
      await api.deleteSubject(id);
    } catch (e) { }
    setData((prev) => ({ ...prev, subjects: prev.subjects.filter((s) => s.id !== id) }));
  };

  const addGoal = async (goal) => {
    try {
      const res = await api.createGoal(goal);
      const created = res?.goal || res;
      if (created && created.id !== undefined) {
        setData((prev) => ({
          ...prev,
          goals: [...prev.goals.filter((g) => g.id !== created.id), created],
        }));
      }
    } catch (e) {
      const newG = { ...goal, id: Math.random().toString(36).substr(2, 8) };
      setData((prev) => ({ ...prev, goals: [...prev.goals, newG] }));
    }
  };

  const updateGoal = async (id, updates) => {
    try {
      await api.updateGoal(id, updates);
    } catch (e) { }
    setData((prev) => ({
      ...prev,
      goals: prev.goals.map((g) => (g.id === id ? { ...g, ...updates } : g)),
    }));
  };

  const deleteGoal = async (id) => {
    try {
      await api.deleteGoal(id);
    } catch (e) { }
    setData((prev) => ({ ...prev, goals: prev.goals.filter((g) => g.id !== id) }));
  };

  const uploadDoc = async (file) => {
    const res = await api.uploadDocument(file);
    await loadDocuments();
    return res;
  };

  const deleteDoc = async (id) => {
    try {
      await api.deleteDocument(id);
    } catch (e) { }
    await loadDocuments();
  };

  const updateRoutine = async (newRoutine) => {
    const updated = { ...data, routine: { ...data.routine, ...newRoutine } };
    setData(updated);
    try {
      await api.saveAllData(updated);
    } catch (e) { }
  };

  const updateUserProfile = async (newProfile) => {
    const updated = { ...data, user: { ...data.user, ...newProfile } };
    setData(updated);
    try {
      await api.saveAllData(updated);
    } catch (e) { }
  };


  const addHoliday = async (holiday) => {
    try {
      const res = await api.createHoliday(holiday);

      if (!res?.holiday) {
        throw new Error('Holiday was not saved by the backend.');
      }

      // Backend is the source of truth.
      await refreshData();

      return res;
    } catch (e) {
      console.error('Failed to add holiday:', e);
      throw e;
    }
  };

  const updateHoliday = async (id, updates) => {
    try {
      await api.updateHoliday(id, updates);

      // Reload the actual persisted account data.
      await refreshData();
    } catch (e) {
      console.error('Failed to update holiday:', e);
      throw e;
    }
  };
  const deleteHoliday = async (id) => {
    try {
      await api.deleteHoliday(id);

      // Reload persisted data.
      await refreshData();
    } catch (e) {
      console.error('Failed to delete holiday:', e);
      throw e;
    }
  };

  const updateWorkingDays = async (workingDays) => {
    try {
      const days = normalizeWorkingDays(workingDays);

      // Save to backend first
      const res = await api.updateWorkingDays(days);

      // Update local state
      setData((prev) => ({
        ...prev,
        settings: {
          ...(prev.settings || {}),
          workingDays: days
        }
      }));

      // Reload from backend to confirm persistence
      await refreshData();

      return res;
    } catch (error) {
      console.error('Failed to save working days:', error);
      throw error;
    }
  };

  const isHoliday = (dateStr) => {
    if (!dateStr) return { isHoliday: false, reason: '' };
    try {
      const cleanDate = String(dateStr).split('T')[0].trim();
      // 1. Declared holidays take precedence
      const found = (data.holidays || []).find((h) => String(h.date).split('T')[0].trim() === cleanDate);
      if (found) {
        return { isHoliday: true, reason: found.name || 'Holiday' };
      }
      // 2. Check working days configured in settings (default Mon-Sat)
      const parts = cleanDate.split('-');
      if (parts.length === 3) {
        const dt = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const dayName = dayNames[dt.getDay()];
        const workingDays = normalizeWorkingDays(data.settings?.workingDays);
        if (!workingDays.includes(dayName)) {
          return { isHoliday: true, reason: `Non-working day (${dayName})` };
        }
      }
      return { isHoliday: false, reason: '' };
    } catch (e) {
      return { isHoliday: false, reason: '' };
    }
  };

  const resetAll = async () => {
    try {
      await api.resetAllData();
    } catch (e) { }
    // Clear old shared and user-specific localStorage backup keys
    localStorage.removeItem('lifeos_local_backup');
    if (authUser?.id) {
      localStorage.removeItem(`lifeos_local_backup_${authUser.id}`);
    }
    // Also clear other potentially stale local storage
    localStorage.removeItem('lifeos_theme');
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('lifeos_local_backup_')) {
        localStorage.removeItem(key);
      }
    }
    setData({
      user: null,
      routine: {
        wakeTime: '07:00',
        sleepTime: '23:00',
        collegeStart: '09:00',
        collegeEnd: '16:00',
        studyHours: 3,
        breakPreference: '15 mins per 45 mins',
        preferredSubjects: [],
      },
      settings: {
        onboardingCompleted: false,
        workingDays: DEFAULT_WORKING_DAYS,
      },
      tasks: [],
      subjects: [],
      events: [],
      goals: [],
      documents: [],
      activity: [],
      holidays: [],
    });
  };

  const value = {
    data,
    setData,
    activeTab,
    setActiveTab,
    theme,
    toggleTheme,
    searchQuery,
    setSearchQuery,
    loading,
    backendOnline,
    geminiInfo,
    setGeminiInfo,
    notifications,
    refreshData,
    handleOnboardingComplete,
    addTask,
    updateTask,
    deleteTask,
    addEvent,
    updateEvent,
    deleteEvent,
    updateWorkingDays,
    addSubject,
    updateSubject,
    deleteSubject,
    addGoal,
    updateGoal,
    deleteGoal,
    addHoliday,
    updateHoliday,
    deleteHoliday,
    isHoliday,
    uploadDoc,
    deleteDoc,
    loadDocuments,
    updateRoutine,
    updateUserProfile,
    resetAll,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
