export function getTodayId() {
  return new Date().toISOString().split('T')[0];
}
