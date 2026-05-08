export const SCHEMA_VERSION = "1.0.0";
export const MAX_PAYLOAD_BYTES = 1_500_000;
export const DEBUG_WEEK_LIMIT = 50;

export function currentSurvey(now = new Date()) {
  const y = now.getUTCFullYear();
  const windows = [
    { survey_id: `anki-census-${y}-1`, start: `${y}-06-01`, end: `${y}-06-10`, reminder_start: `${y}-05-22` },
    { survey_id: `anki-census-${y}-2`, start: `${y}-12-10`, end: `${y}-12-20`, reminder_start: `${y}-11-30` },
  ];
  const today = now.toISOString().slice(0, 10);
  for (const w of windows) {
    if (today <= w.end) return w;
  }
  return { survey_id: `anki-census-${y + 1}-1`, start: `${y + 1}-06-01`, end: `${y + 1}-06-10`, reminder_start: `${y + 1}-05-22` };
}

export function isWithinWindow(surveyId, now = new Date()) {
  const y = Number((surveyId || "").match(/(\d{4})/)?.[1]);
  if (!y) return false;
  const windows = [
    { survey_id: `anki-census-${y}-1`, start: `${y}-06-01`, end: `${y}-06-10` },
    { survey_id: `anki-census-${y}-2`, start: `${y}-12-10`, end: `${y}-12-20` },
  ];
  const today = now.toISOString().slice(0, 10);
  const w = windows.find(x => x.survey_id === surveyId);
  return !!w && today >= w.start && today <= w.end;
}
