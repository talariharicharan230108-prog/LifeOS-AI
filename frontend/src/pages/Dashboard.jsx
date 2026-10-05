import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  Calendar,
  GraduationCap,
  Target,
  ArrowRight,
  TrendingUp,
  Plus,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import * as api from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Dashboard() {
  const { data, setActiveTab, addTask, addEvent, isHoliday, refreshData } = useApp();
  const [dailySummary, setDailySummary] = useState('');
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [planningToday, setPlanningToday] = useState(false);
  const [planMessage, setPlanMessage] = useState('');

  const userName = data?.user?.name || 'Student';
  const todayStr = new Date().toISOString().split('T')[0];

  // Load real AI daily summary
  useEffect(() => {
    let isMounted = true;
    async function loadSummary() {
      try {
        setLoadingSummary(true);
        const res = await api.fetchDailySummary();
        if (isMounted && res?.summary) {
          setDailySummary(res.summary);
        }
      } catch (err) {
        if (isMounted) {
          const pending = data?.tasks?.filter((t) => !t.completed) || [];
          setDailySummary(
            `Good day! You have ${pending.length} pending task(s). Keep up with your study routine!`
          );
        }
      } finally {
        if (isMounted) setLoadingSummary(false);
      }
    }
    loadSummary();
    return () => {
      isMounted = false;
    };
  }, [data?.tasks]);

  const handleGenerateTodaySchedule = async () => {
    try {
      setPlanningToday(true);
      setPlanMessage('');
      const res = await api.generateAIPlan(todayStr);
      setPlanMessage(res?.message || 'Schedule generated for today!');
      // Refresh calendar events immediately
      if (typeof refreshData === 'function') {
        refreshData();
      }
    } catch (err) {
      setPlanMessage('Failed to generate schedule. Please try again.');
    } finally {
      setPlanningToday(false);
    }
  };

  // Metrics from real data
  const totalTasks = data?.tasks?.length || 0;
  const completedTasks = data?.tasks?.filter((t) => t.completed).length || 0;
  const pendingTasks = totalTasks - completedTasks;
  const taskProgress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  const todayEvents = (data?.events || []).filter((e) => e.date === todayStr);

  const upcomingDeadlines = (data?.tasks || [])
    .filter((t) => !t.completed && t.deadline)
    .sort((a, b) => (a.deadline > b.deadline ? 1 : -1))
    .slice(0, 3);

  const upcomingExams = (data?.subjects || []).filter((s) => s.examDate);

  const activeGoals = data?.goals?.slice(0, 3) || [];
  const holidayStatus = isHoliday ? isHoliday(todayStr) : { isHoliday: false };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-700 via-indigo-600 to-violet-600 text-white p-7 shadow-xl shadow-indigo-700/20">
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur-md text-xs font-medium">
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>LifeOS AI Planning Assistant</span>
              </div>
              {holidayStatus.isHoliday && (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-400 text-slate-900 font-bold text-xs shadow-sm">
                  <span>🏖️ {holidayStatus.reason} (Holiday)</span>
                </div>
              )}
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Good day, {userName}!
            </h2>
            <p className="text-sm text-indigo-100 mt-1 max-w-xl">
              {holidayStatus.isHoliday
                ? `Today is ${holidayStatus.reason}, an official holiday! Academic activities are paused so you can recharge.`
                : 'Here is your academic and life overview for today. Stay focused, honor your routine, and hit your milestones.'}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 w-full md:w-auto">
            <button
              onClick={handleGenerateTodaySchedule}
              disabled={planningToday}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-white text-indigo-700 hover:bg-indigo-50 font-semibold text-xs shadow-md transition transform active:scale-95 disabled:opacity-75"
            >
              <Sparkles className={`w-4 h-4 ${planningToday ? 'animate-spin' : ''}`} />
              {planningToday ? 'Generating Schedule...' : 'Generate AI Schedule for Today'}
            </button>
            <button
              onClick={() => setActiveTab('agent')}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-indigo-900/60 hover:bg-indigo-900/80 text-white font-semibold text-xs border border-white/20 transition"
            >
              Open AI Agent
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {planMessage && (
          <div className="mt-3 inline-block px-3 py-1 bg-emerald-500/20 border border-emerald-300/30 rounded-lg text-xs text-white">
            {planMessage}
          </div>
        )}
      </div>

      {/* AI Daily Summary Card */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm relative overflow-hidden">
        <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mb-2">
          <Sparkles className="w-4 h-4" />
          <span>AI Daily Summary</span>
        </div>
        {loadingSummary ? (
          <LoadingSpinner size="sm" text="Synthesizing daily briefing..." />
        ) : (
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
            "{dailySummary}"
          </p>
        )}
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Completed */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-semibold">Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{completedTasks}</p>
          <span className="text-[10px] text-slate-400 font-medium">of {totalTasks} tasks</span>
        </div>

        {/* Pending */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-semibold">Pending</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{pendingTasks}</p>
          <span className="text-[10px] text-slate-400 font-medium">to complete</span>
        </div>

        {/* Schedule */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-semibold">Today's Schedule</span>
            <Calendar className="w-4 h-4 text-indigo-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{todayEvents.length}</p>
          <span className="text-[10px] text-slate-400 font-medium">active blocks</span>
        </div>

        {/* Deadlines */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-semibold">Deadlines</span>
            <AlertCircle className="w-4 h-4 text-rose-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{upcomingDeadlines.length}</p>
          <span className="text-[10px] text-slate-400 font-medium">upcoming</span>
        </div>

        {/* Upcoming Exams (Replaced Syllabus Progress) */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-semibold">Upcoming Exams</span>
            <GraduationCap className="w-4 h-4 text-violet-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{upcomingExams.length}</p>
          <span className="text-[10px] text-slate-400 font-medium">scheduled</span>
        </div>

        {/* Goals */}
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-semibold">Current Goals</span>
            <Target className="w-4 h-4 text-teal-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{data?.goals?.length || 0}</p>
          <span className="text-[10px] text-slate-400 font-medium">tracked</span>
        </div>
      </div>

      {/* Progress Bar & Routine Status */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Today's Overall Task Completion
          </span>
          <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
            {taskProgress}%
          </span>
        </div>
        <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${taskProgress}%` }}
          />
        </div>
      </div>

      {/* Dual Column: Today's Schedule & High Priority Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Schedule */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-500" />
              Today's Schedule ({todayEvents.length})
            </h3>
            <button
              onClick={() => setActiveTab('calendar')}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
            >
              Open Calendar
            </button>
          </div>

          {todayEvents.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No events scheduled for today yet. Click "Generate AI Schedule for Today" or open Calendar!
            </div>
          ) : (
            <div className="space-y-2.5">
              {todayEvents.map((ev) => (
                <div
                  key={ev.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold px-2 py-1 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                      {ev.startTime} - {ev.endTime}
                    </span>
                    <div>
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{ev.title}</p>
                      <span className="text-[10px] text-slate-400">{ev.subject || ev.type}</span>
                    </div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full capitalize bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                    {ev.type}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Priority Tasks & Deadlines */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-500" />
              Immediate Deadlines & Priority Tasks
            </h3>
            <button
              onClick={() => setActiveTab('tasks')}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
            >
              All Tasks ({totalTasks})
            </button>
          </div>

          {upcomingDeadlines.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No pressing deadlines! Create a task in the Tasks tab to plan ahead.
            </div>
          ) : (
            <div className="space-y-2.5">
              {upcomingDeadlines.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800"
                >
                  <div>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{t.title}</p>
                    <p className="text-[10px] text-slate-400">
                      Subject: {t.subject || 'General'} • Due: {t.deadline}
                    </p>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                      t.priority === 'high'
                        ? 'bg-rose-100 dark:bg-rose-950 text-rose-600 dark:text-rose-400'
                        : 'bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400'
                    }`}
                  >
                    {t.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
