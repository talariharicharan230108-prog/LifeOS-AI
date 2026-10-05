import React, { useState } from 'react';
import { Sparkles, ArrowRight, BookOpen, Clock, Check, Plus, Trash2 } from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function OnboardingModal({ isOpen }) {
  const { handleOnboardingComplete } = useApp();
  const [step, setStep] = useState(1);

  // Step 1: User Profile & Timings
  const [name, setName] = useState('');
  const [college, setCollege] = useState('');
  const [course, setCourse] = useState('B.Tech AI / Computer Science');
  const [wakeTime, setWakeTime] = useState('07:00');
  const [sleepTime, setSleepTime] = useState('23:00');
  const [collegeStart, setCollegeStart] = useState('09:00');
  const [collegeEnd, setCollegeEnd] = useState('16:00');
  const [studyHours, setStudyHours] = useState(3);

  // Step 2: Subjects (empty on start - user can add or skip)
  const [subjects, setSubjects] = useState([]);
  const [newSubName, setNewSubName] = useState('');
  const [newSubTeacher, setNewSubTeacher] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleAddSubject = () => {
    if (!newSubName.trim()) return;
    setSubjects([
      ...subjects,
      {
        id: `sub-${Date.now()}`,
        name: newSubName.trim(),
        teacher: newSubTeacher.trim(),
        credits: 3,
        progress: 0,
        importantTopics: [],
        examDate: '',
        assignments: []
      }
    ]);
    setNewSubName('');
    setNewSubTeacher('');
  };

  const handleRemoveSubject = (id) => {
    setSubjects(subjects.filter(s => s.id !== id));
  };

  const handleFinish = async () => {
    setIsSubmitting(true);
    setError('');
    const userData = {
      name: name.trim() || 'Student',
      college: college.trim() || 'Engineering College',
      course: course.trim(),
    };
    const routineData = {
      wakeTime,
      sleepTime,
      collegeStart,
      collegeEnd,
      studyHours: Number(studyHours),
      breakPreference: '15 mins per 45 mins',
      preferredSubjects: subjects.map(s => s.name)
    };
    try {
      await handleOnboardingComplete(userData, routineData, subjects);
    } catch (err) {
      console.error(err);
      setError('Failed to save onboarding data. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 p-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              Welcome to LifeOS
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Personal AI Life & Study Assistant for FAI Year 2
            </p>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center gap-2 mb-6">
          <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-indigo-600' : 'bg-slate-200 dark:bg-slate-800'}`} />
          <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-indigo-600' : 'bg-slate-200 dark:bg-slate-800'}`} />
        </div>

        {/* STEP 1: Profile & Daily Routine */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Your Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Varun Kumar"
                className="w-full px-3.5 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  College / University
                </label>
                <input
                  type="text"
                  value={college}
                  onChange={(e) => setCollege(e.target.value)}
                  placeholder="e.g. SRM / MIT"
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Course / Term
                </label>
                <input
                  type="text"
                  value={course}
                  onChange={(e) => setCourse(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-2 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-500" />
                Daily Routine Constraints (For AI Planning)
              </h4>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-slate-500 dark:text-slate-400 block mb-0.5">Wake-up Time</label>
                  <input
                    type="time"
                    value={wakeTime}
                    onChange={(e) => setWakeTime(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-slate-500 dark:text-slate-400 block mb-0.5">Sleep Time</label>
                  <input
                    type="time"
                    value={sleepTime}
                    onChange={(e) => setSleepTime(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-slate-500 dark:text-slate-400 block mb-0.5">College Start</label>
                  <input
                    type="time"
                    value={collegeStart}
                    onChange={(e) => setCollegeStart(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-slate-500 dark:text-slate-400 block mb-0.5">College End</label>
                  <input
                    type="time"
                    value={collegeEnd}
                    onChange={(e) => setCollegeEnd(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => setStep(2)}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-indigo-600/20"
              >
                Next: Add Subjects
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Academic Subjects */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-1 flex items-center gap-1.5">
                <BookOpen className="w-4 h-4 text-indigo-500" />
                Add Your Term Subjects
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                LifeOS AI will use these subjects to categorize assignments, plan study blocks, and track exam prep.
              </p>

              {/* Add form */}
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  placeholder="Subject Name (e.g. C++ Programming)"
                  value={newSubName}
                  onChange={(e) => setNewSubName(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
                />
                <input
                  type="text"
                  placeholder="Instructor (optional)"
                  value={newSubTeacher}
                  onChange={(e) => setNewSubTeacher(e.target.value)}
                  className="w-36 px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100"
                />
                <button
                  type="button"
                  onClick={handleAddSubject}
                  className="px-3 py-1.5 bg-slate-800 dark:bg-slate-700 hover:bg-slate-900 text-white rounded-xl text-xs flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </div>

              {/* Subject list */}
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {subjects.length === 0 ? (
                  <div className="p-4 text-center rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-500">
                    No subjects added yet. You can add subjects now or skip and add them later in the Academic section.
                  </div>
                ) : (
                  subjects.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/60 rounded-xl text-xs"
                    >
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-slate-200">{s.name}</p>
                        {s.teacher && <p className="text-[11px] text-slate-500 dark:text-slate-400">{s.teacher}</p>}
                      </div>
                      <button
                        onClick={() => handleRemoveSubject(s.id)}
                        className="text-slate-400 hover:text-rose-500 p-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {error && (
              <div className="pt-2">
                <p className="text-xs font-semibold text-rose-500">{error}</p>
              </div>
            )}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => setStep(1)}
                disabled={isSubmitting}
                className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium disabled:opacity-50"
              >
                Back
              </button>
              <button
                onClick={handleFinish}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-indigo-600/20 active:scale-95 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <span className="animate-pulse">Saving...</span>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    {subjects.length === 0 ? 'Skip & Launch Dashboard' : 'Launch LifeOS Dashboard'}
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
