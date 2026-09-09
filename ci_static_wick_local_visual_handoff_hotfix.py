from pathlib import Path


ROOT = Path(__file__).resolve().parent
PATH = ROOT / "video/video_engine.py"
MARKER = "STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1"


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} mismatch count={count}")
    return text.replace(old, new, 1)


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1 already installed")
        return

    required = (
        "VISUAL_EXPLANATION_RETRIEVAL_V1",
        "STATIC_WICK_VISUAL_EXPLANATION_V1",
        "is_static_wick_explanation_scene",
        "video_url = vertical_video_path",
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise RuntimeError(f"static-wick local visual handoff prerequisites missing: {missing}")

    download_block = '''        # ====================================================\n        # 4. 영상 다운로드\n        # ====================================================\n\n        print(\n            "⬇️ 영상 다운로드 시작..."\n        )\n\n        download_video(\n            video_url,\n            source_video_path,\n        )\n\n        if not os.path.exists(\n            source_video_path\n        ):\n\n            raise RuntimeError(\n                "영상 다운로드 실패: "\n                f"{source_video_path}"\n            )\n\n        # ====================================================\n        # 5. 9:16 변환\n        # ====================================================\n\n        prepare_vertical_video(\n            source_video_path,\n            vertical_video_path,\n            duration,\n        )\n'''

    replacement = '''        # ====================================================\n        # 4-5. 영상 materialization\n        # ====================================================\n\n        # STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1\n        # Visual Explanation Retrieval already rendered the trusted deterministic\n        # static-wick asset directly to vertical_video_path. Treat that local\n        # artifact as authoritative for this exact bounded family instead of\n        # feeding it back through the remote downloader / vertical preparation\n        # path, which can overwrite it with an earlier generic stock source.\n        _static_wick_local_visual_ready = (\n            is_static_wick_explanation_scene(item)\n            and video_url == vertical_video_path\n            and os.path.exists(vertical_video_path)\n        )\n\n        if _static_wick_local_visual_ready:\n            print(\n                "[STATIC_WICK_LOCAL_HANDOFF] "\n                f"scene={idx + 1} source={vertical_video_path} status=preserved"\n            )\n        else:\n            print(\n                "⬇️ 영상 다운로드 시작..."\n            )\n\n            download_video(\n                video_url,\n                source_video_path,\n            )\n\n            if not os.path.exists(\n                source_video_path\n            ):\n\n                raise RuntimeError(\n                    "영상 다운로드 실패: "\n                    f"{source_video_path}"\n                )\n\n            prepare_vertical_video(\n                source_video_path,\n                vertical_video_path,\n                duration,\n            )\n'''

    text = _replace_once(
        text,
        download_block,
        replacement,
        "static-wick local visual materialization block",
    )
    PATH.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")
    print("✅ Static-wick local deterministic visual handoff installed; unrelated render paths unchanged")


if __name__ == "__main__":
    main()
