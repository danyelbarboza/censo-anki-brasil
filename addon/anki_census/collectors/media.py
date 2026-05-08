import os, re
from aqt import mw
from ..buckets import bucket_number, bucket_percent, MEDIA_SIZE_MB, COUNT_BUCKETS_MED

IMG_EXT = {'.jpg','.jpeg','.png','.gif','.webp','.svg','.bmp','.tif','.tiff'}
AUD_EXT = {'.mp3','.wav','.ogg','.m4a','.flac','.aac','.opus'}
VID_EXT = {'.mp4','.webm','.mov','.avi','.mkv','.m4v'}

def _media_dir():
    try: return mw.col.media.dir()
    except Exception: return None

def _scan_files():
    base = _media_dir()
    total = imgs = aud = vid = size = 0
    if not base or not os.path.isdir(base):
        return total, imgs, aud, vid, size
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.startswith('_'): continue
            total += 1
            ext = os.path.splitext(f)[1].lower()
            if ext in IMG_EXT: imgs += 1
            elif ext in AUD_EXT: aud += 1
            elif ext in VID_EXT: vid += 1
            try: size += os.path.getsize(os.path.join(root, f))
            except Exception: pass
    return total, imgs, aud, vid, size

def _field_media_ratios(sample_limit=20000):
    total = img = aud = vid = 0
    try:
        rows = mw.col.db.all("select flds from notes limit ?", sample_limit)
    except Exception:
        return None, None, None
    for (flds,) in rows:
        total += 1
        text = flds or ""
        low = text.lower()
        if '<img' in low or re.search(r'\.(jpg|jpeg|png|gif|webp|svg|bmp)', low): img += 1
        if '[sound:' in low or re.search(r'\.(mp3|wav|ogg|m4a|flac|aac|opus)', low): aud += 1
        if re.search(r'\.(mp4|webm|mov|avi|mkv|m4v)', low): vid += 1
    if total == 0: return None, None, None
    return 100*img/total, 100*aud/total, 100*vid/total

def collect_media():
    total, imgs, aud, vid, size = _scan_files()
    img_note_pct, aud_note_pct, vid_note_pct = _field_media_ratios()
    return {
        "media_file_count_bucket": bucket_number(total, COUNT_BUCKETS_MED),
        "media_folder_size_bucket": bucket_number(int(size/1024/1024), MEDIA_SIZE_MB),
        "image_file_ratio_bucket": bucket_percent(100*imgs/total if total else None),
        "audio_file_ratio_bucket": bucket_percent(100*aud/total if total else None),
        "video_file_ratio_bucket": bucket_percent(100*vid/total if total else None),
        "notes_with_images_ratio_bucket": bucket_percent(img_note_pct),
        "notes_with_audio_ratio_bucket": bucket_percent(aud_note_pct),
        "notes_with_video_ratio_bucket": bucket_percent(vid_note_pct),
    }
