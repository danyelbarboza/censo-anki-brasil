function safeJson(s) { try { return JSON.parse(s); } catch { return null; } }
function inc(map, key) { if (key === undefined || key === null || key === "") key = "Não informado"; map[key] = (map[key] || 0) + 1; }
function topMap(map) { return Object.entries(map).sort((a,b)=>b[1]-a[1]).map(([name,count])=>({name,count})); }
function isCensusAddon(ad) {
  const name = String(ad?.name || "").trim().toLowerCase();
  return name === "censo anki brasil";
}

export async function aggregateResults(db) {
  const rows = await db.prepare("SELECT survey_id, payload_json FROM census_responses ORDER BY created_at DESC").all();
  const bySurvey = {};
  for (const row of rows.results || []) {
    const p = safeJson(row.payload_json); if (!p) continue;
    const sid = row.survey_id;
    bySurvey[sid] ||= {
      total_responses: 0,
      addons: {}, fsrs: {}, fsrs_preset_ratio: {}, anki_versions: {}, platforms: {}, countries: {}, states: {}, primary_areas: {}, age: {}, levels: {}, experience: {},
      cards: {}, notes: {}, decks: {}, cards_in_review_state: {}, reviews_30: {}, study_days_30: {}, retention_30: {}, media_images: {}, media_audio: {}, cloze: {}
    };
    const a = bySurvey[sid]; a.total_responses++;
    inc(a.anki_versions, p.environment?.anki_version);
    inc(a.platforms, p.environment?.platform);
    const prof = p.profile_optional?.values || {};
    inc(a.countries, prof.country);
    inc(a.states, prof.state);
    inc(a.primary_areas, prof.primary_area);
    inc(a.age, prof.age_bucket);
    inc(a.levels, prof.self_assessed_level);
    inc(a.experience, prof.anki_experience);
    inc(a.fsrs, p.scheduling?.fsrs_enabled ? "FSRS ativado" : "FSRS desativado");
    inc(a.fsrs_preset_ratio, p.scheduling?.fsrs_enabled_preset_ratio_bucket);
    inc(a.cards, p.collection?.card_count_bucket);
    inc(a.notes, p.collection?.note_count_bucket);
    inc(a.decks, p.collection?.deck_count_bucket);
    inc(a.cards_in_review_state, p.collection?.cards_in_review_state_bucket || p.collection?.review_cards_bucket);
    inc(a.reviews_30, p.activity?.last_30_days?.reviews_bucket);
    inc(a.study_days_30, p.activity?.last_30_days?.study_days_bucket);
    inc(a.retention_30, p.activity?.last_30_days?.retention_bucket);
    inc(a.media_images, p.media?.notes_with_images_ratio_bucket);
    inc(a.media_audio, p.media?.notes_with_audio_ratio_bucket);
    inc(a.cloze, p.templates?.cloze_note_ratio_bucket);
    for (const ad of p.addons?.items || []) {
      if (isCensusAddon(ad)) continue;
      const label = ad.id ? `${ad.name} (${ad.id})` : `${ad.name} (local)`;
      inc(a.addons, label);
    }
  }
  const out = {};
  for (const [sid, a] of Object.entries(bySurvey)) {
    out[sid] = {
      total_responses: a.total_responses,
      top_addons: topMap(a.addons),
      fsrs: topMap(a.fsrs),
      fsrs_enabled_preset_ratio: topMap(a.fsrs_preset_ratio),
      anki_versions: topMap(a.anki_versions),
      operating_systems: topMap(a.platforms),
      countries: topMap(a.countries),
      brazil_states: topMap(a.states),
      primary_areas: topMap(a.primary_areas),
      age_buckets: topMap(a.age),
      self_assessed_levels: topMap(a.levels),
      anki_experience: topMap(a.experience),
      card_count_buckets: topMap(a.cards),
      note_count_buckets: topMap(a.notes),
      deck_count_buckets: topMap(a.decks),
      cards_in_review_state_buckets: topMap(a.cards_in_review_state),
      reviews_last_30_days: topMap(a.reviews_30),
      study_days_last_30_days: topMap(a.study_days_30),
      retention_last_30_days: topMap(a.retention_30),
      notes_with_images: topMap(a.media_images),
      notes_with_audio: topMap(a.media_audio),
      cloze_ratio: topMap(a.cloze),
    };
  }
  return out;
}

export function resultsHtml(results) {
  const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  let body = `<html><head><meta charset="utf-8"><title>Censo Anki Brasil - Resultados</title><style>body{font-family:system-ui;margin:32px;max-width:1100px}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #ddd;padding:8px}th{text-align:left;background:#f4f4f4}section{margin-bottom:36px}</style></head><body><h1>Censo Anki Brasil - Resultados públicos</h1>`;
  for (const [sid, data] of Object.entries(results)) {
    body += `<section><h2>${esc(sid)}</h2><p><b>Total de respostas:</b> ${data.total_responses}</p>`;
    for (const key of Object.keys(data)) {
      if (key === 'total_responses') continue;
      body += `<h3>${esc(key)}</h3><table><tr><th>Categoria</th><th>Contagem</th></tr>`;
      for (const item of data[key].slice(0, 50)) body += `<tr><td>${esc(item.name)}</td><td>${item.count}</td></tr>`;
      body += `</table>`;
    }
    body += `</section>`;
  }
  body += `</body></html>`;
  return body;
}
