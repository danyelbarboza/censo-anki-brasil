from aqt import mw
from ..buckets import bucket_number, COUNT_BUCKETS_SMALL, COUNT_BUCKETS_MED, CARD_BUCKETS, NOTE_BUCKETS

def _scalar(sql, *args, default=0):
    try:
        return mw.col.db.scalar(sql, *args) or 0
    except Exception:
        return default

def collect_collection():
    cards = _scalar("select count() from cards")
    notes = _scalar("select count() from notes")
    decks = 0
    note_types = 0
    try: decks = len(mw.col.decks.all_names_and_ids())
    except Exception:
        try: decks = len(mw.col.decks.all())
        except Exception: decks = 0
    try: note_types = len(mw.col.models.all_names_and_ids())
    except Exception:
        try: note_types = len(mw.col.models.all())
        except Exception: note_types = 0
    tag_count = _scalar("select count(distinct tag) from tags", default=0)
    new_cards = _scalar("select count() from cards where queue = 0")
    learning = _scalar("select count() from cards where queue in (1,3)")
    review = _scalar("select count() from cards where type = 2")
    suspended = _scalar("select count() from cards where queue = -1")
    buried = _scalar("select count() from cards where queue in (-2,-3)")
    due_today = _scalar("select count() from cards where queue = 2 and due <= ?", getattr(mw.col.sched, 'today', 0))
    return {
        "deck_count_bucket": bucket_number(decks, COUNT_BUCKETS_SMALL),
        "note_count_bucket": bucket_number(notes, NOTE_BUCKETS),
        "card_count_bucket": bucket_number(cards, CARD_BUCKETS),
        "note_type_count_bucket": bucket_number(note_types, COUNT_BUCKETS_SMALL),
        "tag_count_bucket": bucket_number(tag_count, COUNT_BUCKETS_MED),
        "new_cards_bucket": bucket_number(new_cards, COUNT_BUCKETS_MED),
        "learning_cards_bucket": bucket_number(learning, COUNT_BUCKETS_MED),
        "cards_in_review_state_bucket": bucket_number(review, CARD_BUCKETS),
        "suspended_cards_bucket": bucket_number(suspended, COUNT_BUCKETS_MED),
        "buried_cards_bucket": bucket_number(buried, COUNT_BUCKETS_MED),
        "due_today_bucket": bucket_number(due_today, COUNT_BUCKETS_MED),
    }
