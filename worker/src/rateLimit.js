import { DEBUG_WEEK_LIMIT } from "./config.js";

export async function checkDebugLimit(db, userId) {
  const row = await db.prepare(
    "SELECT COUNT(*) as c FROM debug_submissions WHERE user_id = ? AND datetime(created_at) >= datetime('now', '-7 days')"
  ).bind(userId || "unknown").first();
  return Number(row?.c || 0) < DEBUG_WEEK_LIMIT;
}
