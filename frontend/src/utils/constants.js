export const DEFAULT_WORKING_DAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday'
];

export const VALID_DAYS = [
  'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
];

export const normalizeWorkingDays = (value) => {
  if (!Array.isArray(value)) return DEFAULT_WORKING_DAYS;
  const cleaned = value.filter(d => VALID_DAYS.includes(d));
  const unique = [...new Set(cleaned)];
  if (unique.length === 0) return DEFAULT_WORKING_DAYS;
  return unique;
};
