import { currentSurvey, isWithinWindow } from "./config.js";
import { json, html } from "./responses.js";
import { readAndValidateRequest } from "./validation.js";
import { checkDebugLimit } from "./rateLimit.js";
import { aggregateResults, resultsHtml } from "./results.js";

async function handleSubmit(request, env) {
  const { payload, error } = await readAndValidateRequest(request);
  if (error) return json({ ok: false, error: error[1] }, error[0]);
  if (!isWithinWindow(payload.survey_id)) return json({ ok: false, error: "collection_window_closed" }, 403);
  try {
    await env.DB.prepare(
      "INSERT INTO census_responses (user_id, survey_id, schema_version, addon_version, payload_json) VALUES (?, ?, ?, ?, ?)"
    ).bind(payload.user_id, payload.survey_id, payload.schema_version, payload.addon_version || "unknown", JSON.stringify(payload)).run();
    return json({ ok: true });
  } catch (e) {
    if (String(e).includes("UNIQUE")) return json({ ok: false, error: "already_submitted" }, 409);
    return json({ ok: false, error: "database_error" }, 500);
  }
}

async function handleDebugSubmit(request, env) {
  const { payload, error } = await readAndValidateRequest(request);
  if (error) return json({ ok: false, error: error[1] }, error[0]);
  const allowed = await checkDebugLimit(env.DB, payload.user_id);
  if (!allowed) return json({ ok: false, error: "debug_weekly_limit_reached" }, 429);
  await env.DB.prepare(
    "INSERT INTO debug_submissions (user_id, schema_version, addon_version, payload_json) VALUES (?, ?, ?, ?)"
  ).bind(payload.user_id, payload.schema_version, payload.addon_version || "unknown", JSON.stringify(payload)).run();
  return json({ ok: true, mode: "developer_test" });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname === "/config") return json({ ok: true, ...currentSurvey(new Date()), results_url: `${url.origin}/results.html` });
      if (url.pathname === "/submit") return handleSubmit(request, env);
      if (url.pathname === "/debug-submit") return handleDebugSubmit(request, env);
      if (url.pathname === "/results") return json({ ok: true, results: await aggregateResults(env.DB) });
      if (url.pathname === "/results.html" || url.pathname === "/") return html(resultsHtml(await aggregateResults(env.DB)));
      return json({ ok: false, error: "not_found" }, 404);
    } catch (e) {
      return json({ ok: false, error: "internal_error" }, 500);
    }
  }
};
