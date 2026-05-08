import { SCHEMA_VERSION, MAX_PAYLOAD_BYTES } from "./config.js";

const ALLOWED_TOP = new Set(["survey_id","schema_version","addon_version","submitted_at_client","mode","user_id","environment","profile_optional","addons","collection","scheduling","activity","templates","media","analysis"]);

export async function readAndValidateRequest(request) {
  if (request.method !== "POST") return { error: [405, "method_not_allowed"] };
  const ct = request.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return { error: [400, "invalid_content_type"] };
  const text = await request.text();
  if (text.length > MAX_PAYLOAD_BYTES) return { error: [413, "payload_too_large"] };
  let payload;
  try { payload = JSON.parse(text); } catch { return { error: [400, "invalid_json"] }; }
  if (!payload || typeof payload !== "object") return { error: [400, "invalid_payload"] };
  if (payload.schema_version !== SCHEMA_VERSION) return { error: [400, "unsupported_schema_version"] };
  if (!/^anki-census-\d{4}-[12]$/.test(payload.survey_id || "")) return { error: [400, "invalid_survey_id"] };
  if (!/^[A-Z2-9]{10}$/.test(payload.user_id || "")) return { error: [400, "invalid_user_id"] };
  const cleaned = {};
  for (const [k, v] of Object.entries(payload)) {
    if (ALLOWED_TOP.has(k)) cleaned[k] = v;
  }
  cleaned.schema_version = SCHEMA_VERSION;
  return { payload: cleaned };
}
