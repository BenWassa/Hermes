export function sanitizeJsonInput(rawInput) {
  return rawInput
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/, '')
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/\u00a0/g, ' ')
    .replace(/[\u200b-\u200d\uFEFF]/g, '');
}
