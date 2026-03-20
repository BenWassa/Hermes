export function getTodayId() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const localDateId = `${year}-${month}-${day}`;
  
  console.log('Hermes getTodayId:', {
    systemIso: new Date().toISOString().split('T')[0],
    localDateId: localDateId,
    timestamp: d.toString()
  });
  
  return localDateId;
}
