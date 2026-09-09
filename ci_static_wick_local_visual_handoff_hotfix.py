from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENGINE_PATH = ROOT / "video/video_engine.py"
DOWNLOADER_PATH = ROOT / "video/video_downloader.py"
MARKER = "STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1"
SCHEME = "static-wick-local://"


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} mismatch count={count}")
    return text.replace(old, new, 1)


def patch_engine():
    text = ENGINE_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        return
    required = (
        "VISUAL_EXPLANATION_RETRIEVAL_V1",
        "STATIC_WICK_VISUAL_EXPLANATION_V1",
        "is_static_wick_explanation_scene",
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise RuntimeError(f"static-wick local handoff engine prerequisites missing: {missing}")

    anchor = '''            if still_result:\n                video_url = vertical_video_path\n'''
    replacement = '''            if still_result:\n                video_url = vertical_video_path\n                # STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1\n                # Mark only the trusted static-wick deterministic asset as a\n                # local handoff. The common materialization path remains intact.\n                if is_static_wick_explanation_scene(item):\n                    video_url = "static-wick-local://" + vertical_video_path\n                    print(\n                        "[STATIC_WICK_LOCAL_HANDOFF] "\n                        f"scene={idx + 1} source={vertical_video_path} status=marked"\n                    )\n'''
    text = _replace_once(text, anchor, replacement, "static-wick local handoff marker")
    ENGINE_PATH.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")


def patch_downloader():
    text = DOWNLOADER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "def download_video(" not in text:
        raise RuntimeError("static-wick local handoff download_video anchor missing")

    patch = r'''

# STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1
# Preserve a deterministic explanation that was already rendered locally.
# All remote URLs and all unrelated local behavior delegate unchanged.
_STATIC_WICK_LOCAL_HANDOFF_PREVIOUS_DOWNLOAD_VIDEO = download_video


def download_video(video_url, output_path, requests_module=requests):
    value = str(video_url or "")
    prefix = "static-wick-local://"
    if not value.startswith(prefix):
        return _STATIC_WICK_LOCAL_HANDOFF_PREVIOUS_DOWNLOAD_VIDEO(
            video_url,
            output_path,
            requests_module=requests_module,
        )

    import shutil

    source_path = value[len(prefix):]
    if not source_path or not os.path.isfile(source_path):
        raise RuntimeError(
            "static-wick local deterministic visual missing: "
            f"{source_path}"
        )
    if os.path.getsize(source_path) <= 0:
        raise RuntimeError(
            "static-wick local deterministic visual is empty: "
            f"{source_path}"
        )

    if os.path.abspath(source_path) != os.path.abspath(output_path):
        shutil.copyfile(source_path, output_path)

    if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
        raise RuntimeError(
            "static-wick local deterministic handoff failed: "
            f"{output_path}"
        )

    print(
        "[STATIC_WICK_LOCAL_HANDOFF] "
        f"source={source_path} materialized={output_path} status=preserved"
    )
    return output_path
'''
    DOWNLOADER_PATH.write_text(text.rstrip() + patch + "\n", encoding="utf-8")


def main():
    patch_engine()
    patch_downloader()
    print("✅ Static-wick local deterministic visual handoff installed; common render path preserved")


if __name__ == "__main__":
    main()
