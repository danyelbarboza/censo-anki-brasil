from aqt import mw
from ..buckets import bucket_number, bucket_percent, COUNT_BUCKETS_SMALL

def collect_templates():
    has_cloze = False
    model_count = 0
    card_template_count = 0
    has_css = False
    has_js = False
    cloze_notes = 0
    total_notes = 0
    try:
        models = mw.col.models.all()
        model_count = len(models)
        for m in models:
            if int(m.get("type", 0)) == 1 or "cloze" in str(m.get("name", "")).lower():
                has_cloze = True
            css = m.get("css", "") or ""
            if len(css.strip()) > 20:
                has_css = True
            for tmpl in m.get("tmpls", []):
                card_template_count += 1
                content = (tmpl.get("qfmt", "") or "") + "\n" + (tmpl.get("afmt", "") or "")
                if "<script" in content.lower() or "javascript:" in content.lower():
                    has_js = True
        total_notes = mw.col.db.scalar("select count() from notes") or 0
        cloze_notes = mw.col.db.scalar("select count() from notes where mid in (select id from notetypes where json_extract(config, '$.type') = 1)") or 0
    except Exception:
        pass
    cloze_pct = 100 * cloze_notes / total_notes if total_notes else None
    return {
        "uses_cloze": bool(has_cloze),
        "cloze_note_ratio_bucket": bucket_percent(cloze_pct),
        "note_type_count_bucket": bucket_number(model_count, COUNT_BUCKETS_SMALL),
        "card_template_count_bucket": bucket_number(card_template_count, COUNT_BUCKETS_SMALL),
        "uses_css_customization": bool(has_css),
        "uses_javascript_in_templates": bool(has_js),
    }
