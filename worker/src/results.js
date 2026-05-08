function safeJson(s) { try { return JSON.parse(s); } catch { return null; } }
function inc(map, key) { if (key === undefined || key === null || key === "") key = "Não informado"; map[key] = (map[key] || 0) + 1; }
function topMap(map) { return Object.entries(map).sort((a,b)=>b[1]-a[1]).map(([name,count])=>({name,count})); }
function isCensusAddon(ad) { return String(ad?.name || "").trim().toLowerCase() === "censo anki brasil"; }
function parsePercent(value) {
  if (value === undefined || value === null) return null;
  const s = String(value).replace(",", ".").trim();
  const exact = s.match(/^(\d+(?:\.\d+)?)%$/);
  if (exact) return Number(exact[1]);
  const range = s.match(/^(?:>)?(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)%$/);
  if (range) return (Number(range[1]) + Number(range[2])) / 2;
  return null;
}
function parseBucketMid(value) {
  if (value === undefined || value === null) return null;
  const s = String(value).replace(/\./g, "").replace(",", ".");
  if (s === "sem limite") return null;
  if (s.includes("%")) return parsePercent(value);
  const nums = [...s.matchAll(/\d+(?:\.\d+)?/g)].map(m => Number(m[0]));
  if (!nums.length) return null;
  return nums.length >= 2 ? (nums[0] + nums[nums.length - 1]) / 2 : nums[0];
}
function avg(values) {
  const nums = values.filter(v => typeof v === "number" && Number.isFinite(v));
  if (!nums.length) return null;
  return Math.round((nums.reduce((a,b)=>a+b,0) / nums.length) * 100) / 100;
}
const REGION_BY_STATE = {
  AC:"Norte", AP:"Norte", AM:"Norte", PA:"Norte", RO:"Norte", RR:"Norte", TO:"Norte",
  AL:"Nordeste", BA:"Nordeste", CE:"Nordeste", MA:"Nordeste", PB:"Nordeste", PE:"Nordeste", PI:"Nordeste", RN:"Nordeste", SE:"Nordeste",
  DF:"Centro-Oeste", GO:"Centro-Oeste", MT:"Centro-Oeste", MS:"Centro-Oeste",
  ES:"Sudeste", MG:"Sudeste", RJ:"Sudeste", SP:"Sudeste",
  PR:"Sul", RS:"Sul", SC:"Sul",
};
function newComparisonGroup() {
  return {
    response_count: 0,
    retention30Values: [], retention180Values: [],
    reviews30Values: [], studyTime30Values: [], studyDays30Values: [],
    notesWithAudioValues: [], notesWithImagesValues: [], fsrsPresetRatioValues: [],
    rate30: { again: [], hard: [], good: [], easy: [] },
    rate180: { again: [], hard: [], good: [], easy: [] },
    distributions: {
      card_count_buckets: {}, note_count_buckets: {}, deck_count_buckets: {}, enabled_addon_count_buckets: {},
      reviews_last_30_days: {}, study_days_last_30_days: {}, study_time_last_30_days: {}, retention_last_30_days: {},
      notes_with_audio: {}, notes_with_images: {}, fsrs_enabled_preset_ratio: {},
    }
  };
}
function pushNum(arr, val) { if (typeof val === "number" && Number.isFinite(val)) arr.push(val); }
function addComparison(group, p) {
  group.response_count++;
  const d = group.distributions;
  inc(d.card_count_buckets, p.collection?.card_count_bucket);
  inc(d.note_count_buckets, p.collection?.note_count_bucket);
  inc(d.deck_count_buckets, p.collection?.deck_count_bucket);
  inc(d.enabled_addon_count_buckets, p.addons?.enabled_addon_count_bucket);
  inc(d.reviews_last_30_days, p.activity?.last_30_days?.reviews_bucket);
  inc(d.study_days_last_30_days, p.activity?.last_30_days?.study_days_bucket);
  inc(d.study_time_last_30_days, p.activity?.last_30_days?.study_time_bucket);
  inc(d.retention_last_30_days, p.activity?.last_30_days?.retention_bucket);
  inc(d.notes_with_audio, p.media?.notes_with_audio_ratio_bucket);
  inc(d.notes_with_images, p.media?.notes_with_images_ratio_bucket);
  inc(d.fsrs_enabled_preset_ratio, p.scheduling?.fsrs_enabled_preset_ratio_bucket);
  pushNum(group.retention30Values, parsePercent(p.activity?.last_30_days?.retention_bucket));
  pushNum(group.retention180Values, parsePercent(p.activity?.last_180_days?.retention_bucket));
  pushNum(group.reviews30Values, parseBucketMid(p.activity?.last_30_days?.reviews_bucket));
  pushNum(group.studyTime30Values, parseBucketMid(p.activity?.last_30_days?.study_time_bucket));
  pushNum(group.studyDays30Values, parseBucketMid(p.activity?.last_30_days?.study_days_bucket));
  pushNum(group.notesWithAudioValues, parsePercent(p.media?.notes_with_audio_ratio_bucket));
  pushNum(group.notesWithImagesValues, parsePercent(p.media?.notes_with_images_ratio_bucket));
  pushNum(group.fsrsPresetRatioValues, parsePercent(p.scheduling?.fsrs_enabled_preset_ratio_bucket));
  pushNum(group.rate30.again, parsePercent(p.activity?.last_30_days?.again_rate_bucket));
  pushNum(group.rate30.hard, parsePercent(p.activity?.last_30_days?.hard_rate_bucket));
  pushNum(group.rate30.good, parsePercent(p.activity?.last_30_days?.good_rate_bucket));
  pushNum(group.rate30.easy, parsePercent(p.activity?.last_30_days?.easy_rate_bucket));
  pushNum(group.rate180.again, parsePercent(p.activity?.last_180_days?.again_rate_bucket));
  pushNum(group.rate180.hard, parsePercent(p.activity?.last_180_days?.hard_rate_bucket));
  pushNum(group.rate180.good, parsePercent(p.activity?.last_180_days?.good_rate_bucket));
  pushNum(group.rate180.easy, parsePercent(p.activity?.last_180_days?.easy_rate_bucket));
}
function serializeComparisonGroup(group) {
  const out = {
    response_count: group.response_count,
    retention_last_30_avg: avg(group.retention30Values),
    retention_last_180_avg: avg(group.retention180Values),
    averages: {
      retention30: avg(group.retention30Values), retention180: avg(group.retention180Values),
      reviews30: avg(group.reviews30Values), studyTime30: avg(group.studyTime30Values), studyDays30: avg(group.studyDays30Values),
      notesWithAudio: avg(group.notesWithAudioValues), notesWithImages: avg(group.notesWithImagesValues), fsrsPresetRatio: avg(group.fsrsPresetRatioValues),
      last_30_rates: { again: avg(group.rate30.again), hard: avg(group.rate30.hard), good: avg(group.rate30.good), easy: avg(group.rate30.easy) },
      last_180_rates: { again: avg(group.rate180.again), hard: avg(group.rate180.hard), good: avg(group.rate180.good), easy: avg(group.rate180.easy) },
    },
    distributions: {}
  };
  for (const [key, map] of Object.entries(group.distributions)) out.distributions[key] = topMap(map);
  return out;
}
function newSurveyAccumulator() {
  return {
    total_responses: 0, unique_user_ids: new Set(), usage_fingerprints: new Set(),
    addons: {}, fsrs: {}, fsrs_preset_ratio: {}, anki_versions: {}, platforms: {}, countries: {}, states: {}, primary_areas: {}, age: {}, levels: {}, experience: {},
    cards: {}, notes: {}, decks: {}, cards_in_review_state: {}, reviews_30: {}, study_days_30: {}, study_time_30: {}, retention_30: {}, media_images: {}, media_audio: {}, cloze: {}, enabled_addon_count: {},
    comparison: { global: newComparisonGroup(), by_region: {}, by_state: {}, by_primary_area: {} }
  };
}

export async function aggregateResults(db) {
  const rows = await db.prepare("SELECT survey_id, payload_json FROM census_responses ORDER BY created_at DESC").all();
  const bySurvey = {};
  for (const row of rows.results || []) {
    const p = safeJson(row.payload_json); if (!p) continue;
    const sid = row.survey_id;
    bySurvey[sid] ||= newSurveyAccumulator();
    const a = bySurvey[sid]; a.total_responses++;
    if (p.user_id) a.unique_user_ids.add(p.user_id);
    if (p.analysis?.usage_fingerprint) a.usage_fingerprints.add(p.analysis.usage_fingerprint);
    inc(a.anki_versions, p.environment?.anki_version); inc(a.platforms, p.environment?.platform);
    const prof = p.profile_optional?.values || {};
    inc(a.countries, prof.country); inc(a.states, prof.state); inc(a.primary_areas, prof.primary_area); inc(a.age, prof.age_bucket); inc(a.levels, prof.self_assessed_level); inc(a.experience, prof.anki_experience);
    inc(a.fsrs, p.scheduling?.fsrs_enabled ? "FSRS ativado" : "FSRS desativado"); inc(a.fsrs_preset_ratio, p.scheduling?.fsrs_enabled_preset_ratio_bucket);
    inc(a.cards, p.collection?.card_count_bucket); inc(a.notes, p.collection?.note_count_bucket); inc(a.decks, p.collection?.deck_count_bucket); inc(a.cards_in_review_state, p.collection?.cards_in_review_state_bucket || p.collection?.review_cards_bucket);
    inc(a.reviews_30, p.activity?.last_30_days?.reviews_bucket); inc(a.study_days_30, p.activity?.last_30_days?.study_days_bucket); inc(a.study_time_30, p.activity?.last_30_days?.study_time_bucket); inc(a.retention_30, p.activity?.last_30_days?.retention_bucket);
    inc(a.media_images, p.media?.notes_with_images_ratio_bucket); inc(a.media_audio, p.media?.notes_with_audio_ratio_bucket); inc(a.cloze, p.templates?.cloze_note_ratio_bucket); inc(a.enabled_addon_count, p.addons?.enabled_addon_count_bucket);
    for (const ad of p.addons?.items || []) { if (isCensusAddon(ad)) continue; const label = ad.id ? `${ad.name} (${ad.id})` : `${ad.name} (local)`; inc(a.addons, label); }
    addComparison(a.comparison.global, p);
    const state = prof.state; const region = REGION_BY_STATE[state]; const area = prof.primary_area;
    if (state) { a.comparison.by_state[state] ||= newComparisonGroup(); addComparison(a.comparison.by_state[state], p); }
    if (region) { a.comparison.by_region[region] ||= newComparisonGroup(); addComparison(a.comparison.by_region[region], p); }
    if (area && area !== "Prefiro não informar") { a.comparison.by_primary_area[area] ||= newComparisonGroup(); addComparison(a.comparison.by_primary_area[area], p); }
  }
  const out = {};
  for (const [sid, a] of Object.entries(bySurvey)) {
    const byRegion = {}; for (const [k, v] of Object.entries(a.comparison.by_region)) byRegion[k] = serializeComparisonGroup(v);
    const byState = {}; for (const [k, v] of Object.entries(a.comparison.by_state)) byState[k] = serializeComparisonGroup(v);
    const byArea = {}; for (const [k, v] of Object.entries(a.comparison.by_primary_area)) byArea[k] = serializeComparisonGroup(v);
    out[sid] = {
      total_responses: a.total_responses, unique_installations: a.unique_user_ids.size, estimated_unique_usage_profiles: a.usage_fingerprints.size,
      top_addons: topMap(a.addons), fsrs: topMap(a.fsrs), fsrs_enabled_preset_ratio: topMap(a.fsrs_preset_ratio), anki_versions: topMap(a.anki_versions), operating_systems: topMap(a.platforms), countries: topMap(a.countries), brazil_states: topMap(a.states), primary_areas: topMap(a.primary_areas), age_buckets: topMap(a.age), self_assessed_levels: topMap(a.levels), anki_experience: topMap(a.experience), card_count_buckets: topMap(a.cards), note_count_buckets: topMap(a.notes), deck_count_buckets: topMap(a.decks), cards_in_review_state_buckets: topMap(a.cards_in_review_state), enabled_addon_count_buckets: topMap(a.enabled_addon_count), reviews_last_30_days: topMap(a.reviews_30), study_days_last_30_days: topMap(a.study_days_30), study_time_last_30_days: topMap(a.study_time_30), retention_last_30_days: topMap(a.retention_30), notes_with_images: topMap(a.media_images), notes_with_audio: topMap(a.media_audio), cloze_ratio: topMap(a.cloze),
      community_comparison: { global: serializeComparisonGroup(a.comparison.global), by_region: byRegion, by_state: byState, by_primary_area: byArea }
    };
  }
  return out;
}

export function resultsHtml(results) {
  const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  let body = `<html><head><meta charset="utf-8"><title>Censo Anki Brasil - Resultados</title><style>body{font-family:system-ui;margin:32px;max-width:1100px;background:#fafafa;color:#111827}table{border-collapse:collapse;width:100%;margin:16px 0;background:white}td,th{border:1px solid #e5e7eb;padding:8px}th{text-align:left;background:#f4f4f5}section{margin-bottom:36px}.card{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:16px;margin:12px 0}</style></head><body><h1>Censo Anki Brasil - Resultados públicos</h1>`;
  for (const [sid, data] of Object.entries(results)) {
    body += `<section><h2>${esc(sid)}</h2><div class="card"><p><b>Total de respostas:</b> ${data.total_responses}</p><p><b>Instalações únicas:</b> ${data.unique_installations}</p><p><b>Perfis de uso estimados:</b> ${data.estimated_unique_usage_profiles}</p></div>`;
    for (const key of Object.keys(data)) {
      if (['total_responses','unique_installations','estimated_unique_usage_profiles','community_comparison'].includes(key)) continue;
      if (!Array.isArray(data[key])) continue;
      body += `<h3>${esc(key)}</h3><table><tr><th>Categoria</th><th>Contagem</th></tr>`;
      for (const item of data[key].slice(0, 50)) body += `<tr><td>${esc(item.name)}</td><td>${item.count}</td></tr>`;
      body += `</table>`;
    }
    if (data.community_comparison?.global) {
      const avg = data.community_comparison.global.averages || {};
      body += `<h3>Comparação da comunidade</h3><div class="card"><p><b>Retenção média global 30d:</b> ${esc(avg.retention30 ?? 'sem dados')}%</p><p><b>Again médio 30d:</b> ${esc(avg.last_30_rates?.again ?? 'sem dados')}%</p><p><b>Good médio 30d:</b> ${esc(avg.last_30_rates?.good ?? 'sem dados')}%</p></div>`;
    }
    body += `</section>`;
  }
  body += `</body></html>`; return body;
}
