import React, { useState } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  CheckSquare,
  AlertCircle,
  X,
  Palmtree,
  Edit2,
  Trash2,
  CalendarCheck,
  Info,
  Sparkles,
  Bot,
  GraduationCap
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { normalizeWorkingDays } from '../utils/constants';
import * as api from '../services/api';
import Modal from '../components/Modal';

// Safe helper to obtain today's local date string (YYYY-MM-DD) without UTC timezone drift
const getTodayLocal = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Safe helper to format display date string consistently
const formatDisplayDate = (dateStr) => {
  if (!dateStr) return '';
  const parts = String(dateStr).split('T')[0].split('-');
  if (parts.length === 3) {
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const d = parseInt(parts[2], 10);
    const dt = new Date(y, m, d);
    if (!isNaN(dt.getTime())) {
      return dt.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric'
      });
    }
  }
  return String(dateStr);
};

export default function CalendarPage() {
  const {
    data,
    addEvent,
    updateEvent,
    deleteEvent,
    addHoliday,
    updateHoliday,
    deleteHoliday,
    isHoliday,
    refreshData
  } = useApp();

  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(() => getTodayLocal());
  
  // Event Modal (Add / Edit)
  const [isEventModalOpen, setIsEventModalOpen] = useState(false);
  const [editingEventId, setEditingEventId] = useState(null);
  const [title, setTitle] = useState('');
  const [type, setType] = useState('work');
  const [startTime, setStartTime] = useState('18:00');
  const [endTime, setEndTime] = useState('19:00');
  const [description, setDescription] = useState('');

  // AI Generation on selected date
  const [generatingAI, setGeneratingAI] = useState(false);
  const [aiPlanMessage, setAiPlanMessage] = useState('');

  // Holiday Modal (Add / Edit)
  const [isHolidayModalOpen, setIsHolidayModalOpen] = useState(false);
  const [editingHolidayId, setEditingHolidayId] = useState(null);
  const [holidayName, setHolidayName] = useState('');
  const [holidayDate, setHolidayDate] = useState(selectedDate);
  const [holidayDescription, setHolidayDescription] = useState('');

  // Month navigation
  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  // Calendar matrix calculation
  const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sunday
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const days = [];
  for (let i = 0; i < firstDayIndex; i++) {
    days.push(null);
  }
  for (let i = 1; i <= daysInMonth; i++) {
    const dayStr = i < 10 ? `0${i}` : `${i}`;
    const mStr = month + 1 < 10 ? `0${month + 1}` : `${month + 1}`;
    days.push(`${year}-${mStr}-${dayStr}`);
  }

  // Selected date details (sanitized YYYY-MM-DD string)
  const cleanSelectedDate = String(selectedDate || getTodayLocal()).split('T')[0].trim();
  const selectedEvents = (data?.events || []).filter((e) => e && String(e.date || '').split('T')[0].trim() === cleanSelectedDate);
  const selectedTasks = (data?.tasks || []).filter((t) => t && String(t.deadline || '').split('T')[0].trim() === cleanSelectedDate);
  const selectedExams = (data?.subjects || []).filter((s) => s && String(s.examDate || '').split('T')[0].trim() === cleanSelectedDate);
  const selectedHolidayStatus = typeof isHoliday === 'function' ? isHoliday(cleanSelectedDate) : { isHoliday: false, reason: '' };
  const workingDays = normalizeWorkingDays(data?.settings?.workingDays);

  const openAddEventModal = () => {
    setEditingEventId(null);
    setTitle('');
    setType('work');
    setStartTime('18:00');
    setEndTime('19:00');
    setDescription('');
    setIsEventModalOpen(true);
  };

  const openEditEventModal = (ev) => {
    setEditingEventId(ev.id);
    setTitle(ev.title || '');
    setType(ev.type || 'work');
    setStartTime(ev.startTime || '18:00');
    setEndTime(ev.endTime || '19:00');
    setDescription(ev.description || '');
    setIsEventModalOpen(true);
  };

  const handleSaveEvent = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (editingEventId) {
      if (typeof updateEvent === 'function') {
        await updateEvent(editingEventId, {
          title: title.trim(),
          date: selectedDate,
          startTime,
          endTime,
          type,
          description: description.trim()
        });
      }
    } else {
      await addEvent({
        title: title.trim(),
        date: selectedDate,
        startTime,
        endTime,
        type,
        source: 'user',
        description: description.trim()
      });
    }

    setIsEventModalOpen(false);
    setTitle('');
    if (typeof refreshData === 'function') {
      refreshData();
    }
  };

  // Generate with AI strictly for the selected date
  const handleGenerateWithAI = async () => {
    try {
      setGeneratingAI(true);
      setAiPlanMessage('');
      const res = await api.generateCalendarSchedule(selectedDate);
      setAiPlanMessage(res?.message || `Schedule generated for ${selectedDate}!`);
      if (typeof refreshData === 'function') {
        await refreshData();
      }
    } catch (err) {
      console.error('Calendar AI generation error:', err);
      setAiPlanMessage('AI schedule generation failed. Please check your Gemini connection.');
    } finally {
      setGeneratingAI(false);
    }
  };

  const openAddHolidayModal = () => {
    setEditingHolidayId(null);
    setHolidayName('');
    setHolidayDate(selectedDate);
    setHolidayDescription('');
    setIsHolidayModalOpen(true);
  };

  const openEditHolidayModal = (h) => {
    setEditingHolidayId(h.id);
    setHolidayName(h.name || '');
    setHolidayDate(h.date || selectedDate);
    setHolidayDescription(h.description || '');
    setIsHolidayModalOpen(true);
  };

  const handleSaveHoliday = async (e) => {
    e.preventDefault();
    if (!holidayName.trim() || !holidayDate) return;

    try {
      if (editingHolidayId) {
        await updateHoliday(editingHolidayId, {
          name: holidayName.trim(),
          date: holidayDate,
          description: holidayDescription.trim()
        });
      } else {
        await addHoliday({
          name: holidayName.trim(),
          date: holidayDate,
          description: holidayDescription.trim()
        });
      }

      setIsHolidayModalOpen(false);
    } catch (err) {
      console.error('Failed to save holiday in Calendar:', err);
      alert('Failed to save holiday. Please try again.');
    }
  };

  const declaredHolidays = data?.holidays || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <CalendarIcon className="w-5 h-5 text-indigo-600" />
            Calendar & Scheduling
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            The central scheduling interface for your academic life, tasks, personal activities, and AI schedules.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
            <button
              onClick={prevMonth}
              className="p-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
              title="Previous Month"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-bold px-3 text-slate-800 dark:text-slate-200 min-w-32 text-center">
              {monthNames[month]} {year}
            </span>
            <button
              onClick={nextMonth}
              className="p-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
              title="Next Month"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={openAddHolidayModal}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded-xl text-xs shadow-md shadow-amber-500/20 transition active:scale-95"
          >
            <Palmtree className="w-4 h-4" />
            + Add Holiday
          </button>

          <button
            onClick={openAddEventModal}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition active:scale-95"
          >
            <Plus className="w-4 h-4" />
            + Add Event
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Month View Grid */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1 text-center text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
            {['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((dName) => {
              const isWork = workingDays.includes(dName);
              return (
                <span
                  key={dName}
                  className={!isWork ? 'text-amber-600 dark:text-amber-400 font-extrabold' : ''}
                >
                  {dName.slice(0, 3)} {!isWork && '(Off)'}
                </span>
              );
            })}
          </div>

          {/* Days grid */}
          <div className="grid grid-cols-7 gap-1.5">
            {days.map((dStr, idx) => {
              if (!dStr) {
                return <div key={`empty-${idx}`} className="h-24 rounded-xl bg-transparent" />;
              }

              const dayNum = parseInt(dStr.split('-')[2], 10);
              const isSelected = dStr === selectedDate;
              const isToday = dStr === new Date().toISOString().split('T')[0];
              const hCheck = isHoliday ? isHoliday(dStr) : { isHoliday: false };

              const dayEvents = (data?.events || []).filter((e) => e.date === dStr);
              const dayTasks = (data?.tasks || []).filter((t) => t.deadline === dStr);
              const dayExams = (data?.subjects || []).filter((s) => s.examDate === dStr);

              return (
                <div
                  key={dStr}
                  onClick={() => {
                    setSelectedDate(dStr);
                    setAiPlanMessage('');
                  }}
                  className={`h-24 p-1.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between select-none ${
                    isSelected
                      ? 'border-indigo-600 ring-2 ring-indigo-500/20 bg-indigo-50/50 dark:bg-indigo-950/40'
                      : hCheck.isHoliday
                      ? 'border-amber-200 dark:border-amber-900/60 bg-amber-50/40 dark:bg-amber-950/20 hover:border-amber-300'
                      : isToday
                      ? 'border-indigo-300 dark:border-indigo-800 bg-slate-50 dark:bg-slate-800/40'
                      : 'border-slate-100 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-bold ${
                        isToday
                          ? 'w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px]'
                          : hCheck.isHoliday
                          ? 'text-amber-700 dark:text-amber-400 font-extrabold'
                          : 'text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {dayNum}
                    </span>

                    {(dayEvents.length > 0 || dayTasks.length > 0 || dayExams.length > 0) && (
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                    )}
                  </div>

                  {/* Holiday Tag */}
                  {hCheck.isHoliday && (
                    <div className="px-1 py-0.5 rounded bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 text-[8.5px] font-bold uppercase tracking-wider truncate border border-amber-300/50 dark:border-amber-800/50">
                      🏖️ {hCheck.reason}
                    </div>
                  )}

                  {/* Micro Indicators */}
                  <div className="space-y-0.5 overflow-hidden">
                    {dayExams.map((s) => (
                      <div
                        key={`exam-${s.id}`}
                        className="truncate text-[8.5px] px-1 py-0.2 rounded bg-violet-100 dark:bg-violet-950/80 text-violet-800 dark:text-violet-300 font-extrabold border border-violet-300/40"
                      >
                        🎓 EXAM: {s.name}
                      </div>
                    ))}
                    {dayTasks.map((t) => (
                      <div
                        key={t.id}
                        className="truncate text-[8.5px] px-1 py-0.2 rounded bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 font-medium"
                      >
                        Due: {t.title}
                      </div>
                    ))}
                    {dayEvents.slice(0, 1).map((e) => (
                      <div
                        key={e.id}
                        className="truncate text-[8.5px] px-1 py-0.2 rounded bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-medium"
                      >
                        {e.title}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Date Details Sidebar */}
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  {formatDisplayDate(cleanSelectedDate)}
                </h3>
                <span className="text-[11px] text-slate-400">
                  {cleanSelectedDate} • {selectedEvents.length} event(s) • {selectedTasks.length} task(s) • {selectedExams.length} exam(s)
                </span>
              </div>

              {/* Generate with AI on selected date */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleGenerateWithAI}
                  disabled={generatingAI}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white font-bold text-xs shadow-md shadow-indigo-600/20 active:scale-95 transition disabled:opacity-50"
                  title="Generate schedule strictly for this date"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${generatingAI ? 'animate-spin' : ''}`} />
                  <span>{generatingAI ? 'Planning...' : 'Generate with AI'}</span>
                </button>

                <button
                  onClick={openAddEventModal}
                  className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100"
                  title="Add event to this date"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

            {aiPlanMessage && (
              <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-700 dark:text-indigo-300 font-medium">
                {aiPlanMessage}
              </div>
            )}

            {/* Exam Day Banner */}
            {selectedExams.map((s) => (
              <div
                key={`exam-banner-${s.id || s.name}`}
                className="p-3.5 rounded-2xl bg-gradient-to-r from-violet-600/15 via-indigo-600/10 to-violet-600/15 border-2 border-violet-500/40 text-xs shadow-sm"
              >
                <div className="flex items-center gap-2 font-bold text-violet-900 dark:text-violet-200 mb-0.5">
                  <GraduationCap className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                  <span>EXAM: {s.name || 'Academic Course'}</span>
                </div>
                <p className="text-[11px] text-violet-800/80 dark:text-violet-300/80">
                  {s.examTime ? `Exam Time: ${s.examTime}` : 'Official Academic Exam Date'} • Recognized as EXAM DAY.
                </p>
              </div>
            ))}

            {/* Holiday Status Banner */}
            {selectedHolidayStatus.isHoliday ? (
              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-amber-800 dark:text-amber-300 mb-0.5">
                  <Palmtree className="w-4 h-4 text-amber-600" />
                  <span>HOLIDAY: {selectedHolidayStatus.reason}</span>
                </div>
                <p className="text-[11px] text-amber-700/80 dark:text-amber-300/80">
                  This date is a non-working day. You can still schedule events or generate work with AI as requested.
                </p>
              </div>
            ) : (
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-800 text-[11px] text-slate-500">
                Regular Working Day
              </div>
            )}

            {/* Empty state when no events, tasks, or exams exist */}
            {selectedExams.length === 0 && selectedTasks.length === 0 && selectedEvents.length === 0 && !selectedHolidayStatus.isHoliday && (
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-center space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">No events, tasks, or exams scheduled for this date.</p>
                <button
                  type="button"
                  onClick={openAddEventModal}
                  className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
                >
                  + Add an activity
                </button>
              </div>
            )}

            {/* Deadlines on this day */}
            <div>
              <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
                Task Deadlines ({selectedTasks.length})
              </h4>
              {selectedTasks.length === 0 ? (
                <p className="text-[11px] text-slate-400">No tasks due on this date.</p>
              ) : (
                <div className="space-y-2">
                  {selectedTasks.map((t) => (
                    <div
                      key={t.id}
                      className="p-2.5 rounded-xl bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200/60 dark:border-rose-900/60 text-xs"
                    >
                      <p className="font-semibold text-rose-900 dark:text-rose-200">{t.title}</p>
                      <p className="text-[10px] text-rose-600 dark:text-rose-400">
                        Priority: {t.priority} • {t.completed ? 'Completed' : 'Pending'}
                      </p>
                      {selectedHolidayStatus.isHoliday && (
                        <p className="text-[10px] text-amber-700 dark:text-amber-300 font-semibold mt-1">
                          ⚠️ Due on a Holiday ({selectedHolidayStatus.reason}). Consider completing earlier!
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Scheduled Sessions & Events */}
            <div>
              <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-500" />
                Scheduled Events ({selectedEvents.length})
              </h4>
              {selectedEvents.length === 0 ? (
                <p className="text-[11px] text-slate-400">No activities scheduled on this day.</p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {selectedEvents.map((e) => (
                    <div
                      key={e.id}
                      className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs flex items-center justify-between"
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <p className="font-semibold text-slate-800 dark:text-slate-200">{e.title}</p>
                          {e.source === 'ai' && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-medium">
                              AI
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {e.isAllDay || !e.startTime || e.startTime === 'All Day'
                            ? 'All Day'
                            : `${e.startTime} - ${e.endTime}`} • {e.type}
                          {e.description ? ` • ${e.description}` : ''}
                        </p>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => openEditEventModal(e)}
                          className="p-1 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded"
                          title="Edit Event"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteEvent(e.id)}
                          className="p-1 text-slate-400 hover:text-rose-500 rounded"
                          title="Delete Event"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Holiday Management List Panel */}
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Palmtree className="w-4 h-4 text-amber-500" />
                Declared Holidays
              </h3>
              <button
                onClick={openAddHolidayModal}
                className="text-[11px] text-amber-600 dark:text-amber-400 font-bold hover:underline"
              >
                + Add Holiday
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {declaredHolidays.length === 0 ? (
                <p className="text-[11px] text-slate-400 py-2">
                  No declared custom holidays. Click "+ Add Holiday" to add college festivals or breaks.
                </p>
              ) : (
                declaredHolidays.map((h) => (
                  <div
                    key={h.id}
                    className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs flex items-center justify-between"
                  >
                    <div>
                      <p className="font-bold text-slate-800 dark:text-slate-200">{h.name}</p>
                      <p className="text-[10px] text-slate-400">
                        {h.date} {h.description ? `• ${h.description}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEditHolidayModal(h)}
                        className="p-1 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded"
                        title="Edit Holiday"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => deleteHoliday(h.id)}
                        className="p-1 text-slate-400 hover:text-rose-500 rounded"
                        title="Delete Holiday"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add / Edit Event Modal */}
      <Modal
        isOpen={isEventModalOpen}
        onClose={() => setIsEventModalOpen(false)}
        title={editingEventId ? `Edit Event on ${selectedDate}` : `Add Event on ${selectedDate}`}
      >
        <form onSubmit={handleSaveEvent} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Event / Activity Name *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. DBMS Assignment Study"
              className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Type
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              >
                <option value="work">Work Session</option>
                <option value="study">Study Session</option>
                <option value="assignment">Assignment</option>
                <option value="exam">Exam Preparation</option>
                <option value="personal">Personal Activity</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Description (Optional)
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Chapter 4 review"
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Start Time
              </label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                End Time
              </label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsEventModalOpen(false)}
              className="px-4 py-2 rounded-xl text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl"
            >
              {editingEventId ? 'Update Event' : 'Save Event'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Holiday Management Modal */}
      <Modal
        isOpen={isHolidayModalOpen}
        onClose={() => setIsHolidayModalOpen(false)}
        title={editingHolidayId ? 'Edit Holiday' : 'Add Declared Holiday'}
      >
        <form onSubmit={handleSaveHoliday} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Holiday Name *
            </label>
            <input
              type="text"
              required
              value={holidayName}
              onChange={(e) => setHolidayName(e.target.value)}
              placeholder="e.g. Dussehra"
              className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Date *
            </label>
            <input
              type="date"
              required
              value={holidayDate}
              onChange={(e) => setHolidayDate(e.target.value)}
              className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Description (Optional)
            </label>
            <input
              type="text"
              value={holidayDescription}
              onChange={(e) => setHolidayDescription(e.target.value)}
              placeholder="e.g. Festival holiday"
              className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsHolidayModalOpen(false)}
              className="px-4 py-2 rounded-xl text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded-xl"
            >
              {editingHolidayId ? 'Update Holiday' : 'Add Holiday'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
