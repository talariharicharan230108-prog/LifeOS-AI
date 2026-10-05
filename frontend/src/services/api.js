// Frontend API service layer communicating with FastAPI backend

const API_BASE = '/api';
const TOKEN_KEY = 'lifeos_token';
const ALT_TOKEN_KEY = 'lifeos_auth_token';
const USER_KEY = 'lifeos_user';

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || localStorage.getItem(ALT_TOKEN_KEY) || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(ALT_TOKEN_KEY, token);
    console.log('[AUTH] TOKEN SAVED');
  } else {
    clearAuthToken();
  }
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ALT_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getSavedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setSavedUser(user) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
}

function authHeaders(extra = {}) {
  const token = getAuthToken();
  const headers = { ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ----------------- AUTHENTICATION -----------------
export async function registerUser({ name, email, password, confirmPassword }) {
  console.log('[AUTH] REGISTER REQUEST', { email });
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password, confirmPassword }),
  });
  console.log('[AUTH] REGISTER RESPONSE STATUS:', res.status);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Registration failed');
  }
  const token = data.token || data.access_token;
  if (token) {
    setAuthToken(token);
  }
  const user = data.user || data;
  if (user && typeof user === 'object' && user.email) {
    setSavedUser(user);
  }
  return { ...data, token, user };
}

export async function loginUser({ email, password }) {
  console.log('[AUTH] LOGIN REQUEST', { email });
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  console.log('[AUTH] LOGIN RESPONSE STATUS:', res.status);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Invalid email or password');
  }
  const token = data.token || data.access_token;
  if (token) {
    setAuthToken(token);
  }
  const user = data.user || data;
  if (user && typeof user === 'object' && user.email) {
    setSavedUser(user);
  }
  return { ...data, token, user };
}

export async function logoutUser() {
  console.log('[AUTH] LOGOUT');
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: authHeaders(),
    });
  } catch (err) {
    console.error('Logout error:', err);
  } finally {
    clearAuthToken();
  }
  return { success: true };
}

export async function fetchCurrentUser() {
  const token = getAuthToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(),
  });
  console.log('[AUTH] /ME RESPONSE STATUS:', res.status);
  if (res.status === 401 || res.status === 403) {
    clearAuthToken();
    return null;
  }
  if (!res.ok) {
    const err = new Error(`Server returned ${res.status}`);
    err.status = res.status;
    throw err;
  }
  const data = await res.json();
  const user = data.user || data;
  if (user && typeof user === 'object' && user.email) {
    setSavedUser(user);
  }
  return user;
}

export async function changeUserPassword({ currentPassword, newPassword, confirmNewPassword }) {
  const res = await fetch(`${API_BASE}/auth/change-password`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ currentPassword, newPassword, confirmNewPassword }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to change password');
  }
  return data;
}

export async function updateUserProfile({ name }) {
  const res = await fetch(`${API_BASE}/auth/profile`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ name }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to update profile');
  }
  return data;
}

export async function fetchUserProfile() {
  const res = await fetch(`${API_BASE}/profile`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch user profile');
  return await res.json();
}

export async function saveUserProfile(profileData) {
  let res = await fetch(`${API_BASE}/profile`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(profileData),
  });
  if (!res.ok) {
    res = await fetch(`${API_BASE}/profile`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(profileData),
    });
  }
  if (!res.ok) throw new Error('Failed to save profile');
  return await res.json();
}

// ----------------- SYSTEM & HEALTH -----------------
export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      headers: authHeaders(),
    });
    return await res.json();
  } catch (err) {
    return { status: 'offline', error: err.message };
  }
}

export async function fetchAllData() {
  const res = await fetch(`${API_BASE}/data`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch data');
  return await res.json();
}

export async function saveAllData(data) {
  const res = await fetch(`${API_BASE}/data`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to save data');
  return await res.json();
}

export async function resetAllData() {
  const res = await fetch(`${API_BASE}/data/reset`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to reset data');
  return await res.json();
}

// ----------------- AI AGENT & PLANNING -----------------
export async function sendAgentMessage(message) {
  const res = await fetch(`${API_BASE}/agent`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Agent error' }));
    throw new Error(err.detail || 'Failed to communicate with AI agent');
  }
  return await res.json();
}

export async function fetchDailySummary() {
  const res = await fetch(`${API_BASE}/agent/summary`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch daily summary');
  return await res.json();
}

export async function generateCalendarSchedule(targetDate) {
  const res = await fetch(`${API_BASE}/calendar/generate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ date: targetDate }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate schedule' }));
    throw new Error(err.detail || 'Failed to generate schedule');
  }
  return await res.json();
}

export async function generateAIPlan(targetDate) {
  return generateCalendarSchedule(targetDate);
}

// ----------------- HOLIDAYS -----------------
export async function fetchHolidays() {
  const res = await fetch(`${API_BASE}/holidays`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch holidays');
  return await res.json();
}

export async function createHoliday(holiday) {
  const res = await fetch(`${API_BASE}/holidays`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(holiday),
  });
  if (!res.ok) throw new Error('Failed to create holiday');
  return await res.json();
}

export async function updateHoliday(holidayId, updates) {
  const res = await fetch(`${API_BASE}/holidays/${holidayId}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update holiday');
  return await res.json();
}

export async function deleteHoliday(holidayId) {
  const res = await fetch(`${API_BASE}/holidays/${holidayId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete holiday');
  return await res.json();
}

export async function checkHoliday(dateStr) {
  const res = await fetch(`${API_BASE}/holidays/check?date=${encodeURIComponent(dateStr)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to check holiday status');
  return await res.json();
}

// ----------------- TASKS -----------------
export async function createTask(task) {
  const res = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(task),
  });
  if (!res.ok) throw new Error('Failed to create task');
  return await res.json();
}

export async function updateTask(taskId, updates) {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update task');
  return await res.json();
}

export async function deleteTask(taskId) {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete task');
  return await res.json();
}

// ----------------- EVENTS (CALENDAR) -----------------
export async function fetchEvents(dateStr = '') {
  const url = dateStr ? `${API_BASE}/events?date=${encodeURIComponent(dateStr)}` : `${API_BASE}/events`;
  const res = await fetch(url, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch events');
  return await res.json();
}

export async function createEvent(event) {
  const res = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(event),
  });
  if (!res.ok) throw new Error('Failed to create event');
  return await res.json();
}

export async function updateEvent(eventId, updates) {
  const res = await fetch(`${API_BASE}/events/${eventId}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update event');
  return await res.json();
}

export async function deleteEvent(eventId) {
  const res = await fetch(`${API_BASE}/events/${eventId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete event');
  return await res.json();
}

// ----------------- SUBJECTS -----------------
export async function createSubject(subject) {
  const res = await fetch(`${API_BASE}/subjects`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(subject),
  });
  if (!res.ok) throw new Error('Failed to create subject');
  return await res.json();
}

export async function updateSubject(subjectId, updates) {
  const res = await fetch(`${API_BASE}/subjects/${subjectId}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update subject');
  return await res.json();
}

export async function deleteSubject(subjectId) {
  const res = await fetch(`${API_BASE}/subjects/${subjectId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete subject');
  return await res.json();
}

// ----------------- GOALS -----------------
export async function fetchGoals() {
  const res = await fetch(`${API_BASE}/goals`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch goals');
  return await res.json();
}

export async function createGoal(goal) {
  const res = await fetch(`${API_BASE}/goals`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(goal),
  });
  if (!res.ok) throw new Error('Failed to create goal');
  return await res.json();
}

export async function updateGoal(goalId, updates) {
  const res = await fetch(`${API_BASE}/goals/${goalId}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update goal');
  return await res.json();
}

export async function deleteGoal(goalId) {
  const res = await fetch(`${API_BASE}/goals/${goalId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete goal');
  return await res.json();
}

// ----------------- ACADEMIC -----------------
export async function fetchAcademicData() {
  const res = await fetch(`${API_BASE}/academic`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch academic data');
  return await res.json();
}

// ----------------- DOCUMENTS -----------------
export async function fetchDocuments(query = '') {
  const url = query ? `${API_BASE}/documents?query=${encodeURIComponent(query)}` : `${API_BASE}/documents`;
  const res = await fetch(url, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch documents');
  const data = await res.json();
  const docs = Array.isArray(data) ? data : (data.documents || []);
  return { documents: docs, status: 'success' };
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const token = getAuthToken();
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || err.message || 'Upload failed');
  }
  return await res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete document');
  return await res.json();
}

export async function askDocumentQA(docId, query) {
  const payload = { doc_id: docId, query, question: query };
  let res = await fetch(`${API_BASE}/documents/qa`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    res = await fetch(`${API_BASE}/documents/query`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Query failed' }));
    throw new Error(err.detail || err.message || 'Failed to query document');
  }
  return await res.json();
}

// ----------------- SETTINGS & AI -----------------
export async function updateApiKey(apiKey) {
  const res = await fetch(`${API_BASE}/settings/key`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) throw new Error('Failed to update API key');
  return await res.json();
}

export async function fetchKeyStatus() {
  const res = await fetch(`${API_BASE}/settings/key/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch key status');
  return await res.json();
}

export async function fetchAIStatus() {
  const res = await fetch(`${API_BASE}/ai/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch AI status');
  return await res.json();
}

export async function testAIConnection() {
  const res = await fetch(`${API_BASE}/ai/test`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to test AI connection');
  return await res.json();
}

export async function fetchWorkingDays() {
  const res = await fetch(`${API_BASE}/settings/working-days`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch working days');
  return await res.json();
}

export async function updateWorkingDays(workingDays) {
  const res = await fetch(`${API_BASE}/settings/working-days`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ workingDays }),
  });
  if (!res.ok) throw new Error('Failed to update working days');
  return await res.json();
}
