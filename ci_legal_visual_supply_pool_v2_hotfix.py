from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} marker mismatch count={text.count(old)}")
    return text.replace(old, new, 1)


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    "    PIXABAY_API_KEY,\n    VIDEO_PROVIDER_PER_PAGE,\n",
    "    PIXABAY_API_KEY,\n    WIKIMEDIA_COMMONS_ENABLED,\n    VIDEO_PROVIDER_PER_PAGE,\n",
    "commons enabled import",
)
text = replace_once(
    text,
    "    search_pixabay_candidates,\n)\n\nfrom config import (\n",
    "    search_pixabay_candidates,\n    search_wikimedia_commons_candidates,\n)\n\nfrom config import (\n",
    "commons search import",
)

commons_block = '''\n    if WIKIMEDIA_COMMONS_ENABLED:\n        try:\n            commons = search_wikimedia_commons_candidates(query, per_page=limit)\n            print(f"[VIDEO_PROVIDER] provider=wikimedia_commons candidates={len(commons)}")\n            provider_results.append(commons)\n        except Exception as exc:\n            print(f"[VIDEO_PROVIDER_SKIP] provider=wikimedia_commons reason={type(exc).__name__}")\n    else:\n        print("[VIDEO_PROVIDER_SKIP] provider=wikimedia_commons reason=disabled")\n'''
text = replace_once(
    text,
    '''    if PIXABAY_API_KEY:\n        try:\n            pixabay = search_pixabay_candidates(query, per_page=limit)\n''',
    commons_block + '''\n    if PIXABAY_API_KEY:\n        try:\n            pixabay = search_pixabay_candidates(query, per_page=limit)\n''',
    "commons provider collection",
)
text = replace_once(
    text,
    '''    if not PIXABAY_API_KEY:\n        return fetch_pexels_video(query)\n''',
    '''    if not PIXABAY_API_KEY and not WIKIMEDIA_COMMONS_ENABLED:\n        return fetch_pexels_video(query)\n''',
    "legacy exact-path guard",
)

path.write_text(text, encoding="utf-8")
print("✅ Legal Visual Supply Pool V2 hotfix applied (license-gated Wikimedia Commons)")
