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

// Returns { valid: bool, errors: string[], warnings: string[] }
export function validateDailyBriefing(parsed) {
  const errors = [];
  const warnings = [];

  if (!parsed.id) errors.push('Missing required field: "id" (YYYY-MM-DD)');
  if (!parsed.date) errors.push('Missing required field: "date"');
  if (!Array.isArray(parsed.today_in_60_seconds)) {
    errors.push('Missing required field: "today_in_60_seconds" (must be array)');
  }

  if (!parsed.what_changed || typeof parsed.what_changed !== 'object') {
    warnings.push('Missing "what_changed" section — recommended for cross-day delta tracking');
  }

  if (Array.isArray(parsed.major_developments)) {
    parsed.major_developments.forEach((dev, i) => {
      const label = dev.headline ? `"${dev.headline.slice(0, 40)}"` : `development[${i}]`;
      if (!dev.story_id) warnings.push(`${label}: missing story_id`);
      if (!dev.driver) warnings.push(`${label}: missing driver`);
      if (!dev.change_type) warnings.push(`${label}: missing change_type`);
      if (!dev.story_stage) warnings.push(`${label}: missing story_stage`);
    });
  }

  return { valid: errors.length === 0, errors, warnings };
}

// Returns { valid: bool, errors: string[], warnings: string[] }
export function validateAmplifier(parsed) {
  const errors = [];
  const warnings = [];

  if (parsed.type !== 'amplifier') errors.push('Field "type" must equal "amplifier"');
  if (!parsed.id) errors.push('Missing required field: "id" (amp-YYYY-MM-DD)');
  if (!parsed.briefing_id) errors.push('Missing required field: "briefing_id"');
  if (!parsed.decision_layer) errors.push('Missing required field: "decision_layer"');

  if (!parsed.scenarios) warnings.push('Missing "scenarios" — recommended for forward path analysis');
  if (!parsed.delta_lens) warnings.push('Missing "delta_lens" — recommended for continuity signal');
  if (!Array.isArray(parsed.driver_decomposition)) {
    warnings.push('Missing "driver_decomposition" — recommended for causal clarity');
  }

  return { valid: errors.length === 0, errors, warnings };
}

// Returns { valid: bool, errors: string[], warnings: string[] }
export function validateSynthesis(parsed) {
  const errors = [];
  const warnings = [];

  if (parsed.type !== 'synthesis') errors.push('Field "type" must equal "synthesis"');
  if (!parsed.id) errors.push('Missing required field: "id"');
  if (!parsed.date_range?.from || !parsed.date_range?.to) {
    errors.push('Missing required field: "date_range" with "from" and "to"');
  }

  if (!Array.isArray(parsed.active_threads) && !Array.isArray(parsed.thematic_arcs)) {
    warnings.push('Synthesis contains no active_threads or thematic_arcs');
  }

  return { valid: errors.length === 0, errors, warnings };
}
