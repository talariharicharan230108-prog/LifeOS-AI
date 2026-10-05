import React, { useState } from 'react';
import {
  GraduationCap,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  BookOpen,
  Award,
  CheckCircle,
  Clock,
  Layers
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import Modal from '../components/Modal';
import EmptyState from '../components/EmptyState';

export default function Academic() {
  const { data, addSubject, updateSubject, deleteSubject } = useApp();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState(null);

  // Form states
  const [name, setName] = useState('');
  const [teacher, setTeacher] = useState('');
  const [credits, setCredits] = useState(3);
  const [progress, setProgress] = useState(0);
  const [topicsStr, setTopicsStr] = useState('');
  const [examDate, setExamDate] = useState('');
  const [examTime, setExamTime] = useState('');

  const openAddModal = () => {
    setEditingSubject(null);
    setName('');
    setTeacher('');
    setCredits(3);
    setProgress(0);
    setTopicsStr('');
    setExamDate('');
    setExamTime('');
    setIsModalOpen(true);
  };

  const openEditModal = (sub) => {
    setEditingSubject(sub);
    setName(sub.name);
    setTeacher(sub.teacher || '');
    setCredits(sub.credits || 3);
    setProgress(sub.progress || 0);
    setTopicsStr(Array.isArray(sub.importantTopics) ? sub.importantTopics.join(', ') : '');
    setExamDate(sub.examDate || '');
    setExamTime(sub.examTime || '');
    setIsModalOpen(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    const topics = topicsStr
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    if (editingSubject) {
      updateSubject(editingSubject.id, {
        name: name.trim(),
        teacher: teacher.trim(),
        credits: Number(credits),
        progress: Number(progress),
        importantTopics: topics,
        examDate,
        examTime: examTime.trim(),
      });
    } else {
      addSubject({
        name: name.trim(),
        teacher: teacher.trim(),
        credits: Number(credits),
        progress: Number(progress),
        importantTopics: topics,
        examDate,
        examTime: examTime.trim(),
      });
    }

    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-indigo-600" />
            Academic Courses & Subjects
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage your enrolled subjects, professors, credits, assignments, and exam dates.
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 active:scale-95 transition"
        >
          <Plus className="w-4 h-4" />
          Add Subject
        </button>
      </div>

      {/* Subjects Grid */}
      {(data?.subjects || []).length === 0 ? (
        <EmptyState
          icon={GraduationCap}
          title="No subjects added yet."
          description="Your academic information will appear here."
          actionText="+ Add Subject"
          onAction={openAddModal}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {data.subjects.map((sub) => {
            const subjectTasks = (data?.tasks || []).filter(
              (t) => t.subject?.toLowerCase() === sub.name?.toLowerCase()
            );
            const pendingTasks = subjectTasks.filter((t) => !t.completed);

            return (
              <div
                key={sub.id}
                className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm hover:shadow-md transition flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        {sub.name}
                      </h3>
                      {sub.teacher && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          {sub.teacher}
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                      {sub.credits} Credits
                    </span>
                  </div>

                  {/* Course Progress */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs mb-1 font-medium">
                      <span className="text-slate-600 dark:text-slate-400">Course Progress</span>
                      <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                        {sub.progress || 0}%
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                        style={{ width: `${sub.progress || 0}%` }}
                      />
                    </div>
                  </div>

                  {/* Focus topics tags */}
                  {sub.importantTopics && sub.importantTopics.length > 0 && (
                    <div className="mb-4">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                        Focus Topics
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {sub.importantTopics.map((top, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                          >
                            {top}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Exam Date & Tasks meta */}
                  <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 space-y-1.5 text-xs text-slate-500 dark:text-slate-400">
                    {sub.examDate ? (
                      <div className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400 font-medium">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>Exam Date: {sub.examDate} {sub.examTime ? `(${sub.examTime})` : ''}</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-slate-400">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>Exam date not set</span>
                      </div>
                    )}

                    <div className="flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{pendingTasks.length} pending assignment(s)</span>
                    </div>
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="flex items-center justify-end gap-1 pt-4 mt-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => openEditModal(sub)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                    title="Edit subject"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => deleteSubject(sub.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition"
                    title="Delete subject"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add / Edit Subject Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingSubject ? 'Edit Subject' : 'Add New Subject'}
      >
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Subject Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Advanced Database Management Systems"
              className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Teacher / Professor
              </label>
              <input
                type="text"
                value={teacher}
                onChange={(e) => setTeacher(e.target.value)}
                placeholder="e.g. Dr. Ramesh"
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Course Credits
              </label>
              <input
                type="number"
                min={1}
                max={8}
                value={credits}
                onChange={(e) => setCredits(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Course Progress ({progress}%)
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={progress}
                onChange={(e) => setProgress(e.target.value)}
                className="w-full mt-2 accent-indigo-600"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Exam Date (Optional)
              </label>
              <input
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Exam Time (Optional)
              </label>
              <input
                type="time"
                value={examTime}
                onChange={(e) => setExamTime(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Important Topics (Optional)
              </label>
              <input
                type="text"
                value={topicsStr}
                onChange={(e) => setTopicsStr(e.target.value)}
                placeholder="e.g. Unit 1, Unit 2"
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-xl text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl"
            >
              {editingSubject ? 'Save Changes' : 'Create Subject'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
