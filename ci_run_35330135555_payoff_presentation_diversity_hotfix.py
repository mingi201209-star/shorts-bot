"""Run 35330135555: make budget-exhausted payoff still reuse visibly distinct.

Authority MP4 is fact/semantic safe and removed the night-vision stock, but
Scenes 4 and 5 reused the same verified physical still with empty presentation
metadata. visual_diversity_preflight correctly saw the repeated asset but passed
it as medium severity.

No new image/Vision/API call is added. When the existing still-generation budget
is already exhausted and a payoff/result must reuse a previously verified still,
render a bounded center-only reverse zoom-out presentation. If that deterministic
presentation cannot re-verify, fall back to the previous verified reuse path.
"""
from pathlib import Path

STILL = Path("video/still_image_fallback.py")
DIVERSITY = Path("quality/visual_diversity_preflight.py")

STILL_MARKER = "# RUN_35330135555_PAYOFF_PRESENTATION_DIVERSITY_V1"
DIVERSITY_MARKER = "# RUN_35330135555_PRESENTATION_LINEAGE_V1"

_STILL_APPEND = r'''

# RUN_35330135555_PAYOFF_PRESENTATION_DIVERSITY_V1
_run_35330135555_previous_reuse_verified_still = _reuse_verified_still


def _run_35330135555_is_payoff_role(scene):
    scene = scene or {}
    values = (
        scene.get("role"),
        scene.get("scene_role"),
        scene.get("causal_role"),
        scene.get("semantic_purpose"),
    )
    joined = " ".join(str(value or "").strip().lower() for value in values)
    return (
        "payoff" in joined
        or "primary_result" in joined
        or "conclusion" in joined
        or joined.strip() == "result"
    )


def _run_35330135555_payoff_reverse_motion(
    image_path,
    output_path,
    duration,
):
    duration = max(1.0, float(duration))
    fade = min(0.35, duration / 4.0)
    fade_out_start = max(0.0, duration - fade)

    # The verified subject was generated large and central by the canonical
    # still contract. Keep the focal region centered and only change scale over
    # time: close inspection -> wider context. This is presentation, not new
    # factual content.
    zoom_expr = "if(eq(on,0),1.1200,max(pzoom-0.0008,1.0200))"
    vf = (
        "scale=1280:1920:force_original_aspect_ratio=increase,"
        "crop=1280:1920,"
        f"zoompan=z='{zoom_expr}':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade:.3f},"
        "format=yuv420p"
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
            "-t", f"{duration:.3f}", "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "payoff reverse-motion ffmpeg failed: " + result.stderr[-1200:]
        )
    if not Path(output_path).exists():
        raise RuntimeError("payoff reverse-motion output missing")


def _run_35330135555_reuse_payoff_presentation(
    scene,
    *,
    output_path,
    duration,
    trigger_reason,
):
    # #416 already prefers a fresh still while a generation slot remains.
    # This path starts only when that existing budget is exhausted.
    if not _run_35330135555_is_payoff_role(scene):
        return None
    if int(_GENERATION_COUNT) < int(STILL_IMAGE_MAX_PER_VIDEO):
        return None

    for signature in _reuse_signatures(scene):
        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        image_path = Path(str(cached.get("image_path") or ""))
        source_id = str(cached.get("source_id") or "")
        if not source_id or not image_path.is_file():
            continue
        if verified_source_use_count(source_id) <= 0:
            continue
        if not _source_reuse_allowed(source_id, scene):
            continue

        try:
            _run_35330135555_payoff_reverse_motion(
                image_path,
                output_path,
                duration,
            )
            verified, evidence = _verify_motion_clip(scene, output_path)
            if not verified:
                Path(output_path).unlink(missing_ok=True)
                continue

            _register_source_use(source_id, scene)
            presentation = "PAYOFF_REVERSE_ZOOM_OUT_CENTER_V1"
            motion_profile = "reverse_zoom_out_center"
            print(
                "[STILL_PRESENTATION] "
                f"scene={_scene_id(scene)} status=payoff_reverse_verified "
                f"source_id={source_id} uses={verified_source_use_count(source_id)} "
                f"generation_count={_GENERATION_COUNT}/{STILL_IMAGE_MAX_PER_VIDEO} "
                f"presentation={presentation}"
            )
            return {
                "path": str(output_path),
                "provider": cached.get("provider", "openai_image"),
                "source_id": source_id,
                "source_asset_id": source_id,
                "mode": "REUSED_VERIFIED_STILL_MOTION_PRESENTATION",
                "tier": 2,
                "visual_state": "TRUE",
                "anchor_matched": len(_anchor_signature(scene)),
                "anchor_total": len(_anchor_signature(scene)),
                "visible_components": list(
                    evidence.get("visible_components", []) or []
                ),
                "presentation_variant": presentation,
                "motion_profile": motion_profile,
            }
        except Exception as exc:
            Path(output_path).unlink(missing_ok=True)
            print(
                "[STILL_PRESENTATION] "
                f"scene={_scene_id(scene)} status=payoff_reverse_failed "
                f"reason={type(exc).__name__} fallback=verified_reuse"
            )

    return None


def _reuse_verified_still(scene, *, output_path, duration, trigger_reason):
    presented = _run_35330135555_reuse_payoff_presentation(
        scene,
        output_path=output_path,
        duration=duration,
        trigger_reason=trigger_reason,
    )
    if presented is not None:
        return presented

    return _run_35330135555_previous_reuse_verified_still(
        scene,
        output_path=output_path,
        duration=duration,
        trigger_reason=trigger_reason,
    )
'''

_DIVERSITY_APPEND = r'''

# RUN_35330135555_PRESENTATION_LINEAGE_V1
_run_35330135555_previous_variant = _variant


def _variant(scene, item):
    item = dict(item or {})
    presentation = str(item.get("presentation_variant") or "").strip().upper()
    motion = str(item.get("motion_profile") or "").strip().lower()
    mode = str(item.get("mode") or "").upper()

    if (
        presentation
        and motion
        and "REUSED_VERIFIED_STILL_MOTION_PRESENTATION" in mode
    ):
        return f"presentation:{presentation}:{motion}"

    return _run_35330135555_previous_variant(scene, item)
'''


def patch_still(text: str) -> str:
    if STILL_MARKER in text:
        return text
    required = (
        "def _reuse_verified_still(",
        "def _verify_motion_clip(",
        "def _source_reuse_allowed(",
        "RUN_35327208962_BOUNDED_STILL_NOVELTY_V1",
        "STILL_IMAGE_MAX_PER_VIDEO",
    )
    if not all(token in text for token in required):
        raise RuntimeError(
            "Run 35330135555 payoff presentation prerequisites missing"
        )
    return text.rstrip() + _STILL_APPEND + "\n"


def patch_diversity(text: str) -> str:
    if DIVERSITY_MARKER in text:
        return text
    required = (
        "def _variant(",
        "def evaluate_visual_diversity(",
        "raw_physical_asset",
    )
    if not all(token in text for token in required):
        raise RuntimeError(
            "Run 35330135555 diversity lineage prerequisites missing"
        )
    return text.rstrip() + _DIVERSITY_APPEND + "\n"


def main() -> None:
    STILL.write_text(
        patch_still(STILL.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    DIVERSITY.write_text(
        patch_diversity(DIVERSITY.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    print(
        "✅ Run 35330135555 payoff presentation diversity installed; "
        "zero new image/Vision/API calls and still budget unchanged"
    )


if __name__ == "__main__":
    main()
