from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# QUESTION_SUBJECT_REUSE_RUN_33371268494_V1"


_HELPERS = r'''

# QUESTION_SUBJECT_REUSE_RUN_33371268494_V1
# A previously verified physical subject may be reused only for a question beat
# that asks about that exact same trusted canonical subject. Mechanism/result
# scenes still require their own explanatory evidence.
def _subject_proof_required_groups(scene):
    # Use the exact resolver that structured still-Vision verification uses.
    # This prevents reuse from silently interpreting a Scene contract differently
    # from the verifier that produced the trusted proof.
    try:
        from video.hook_visual_dominance import _still_vision_required_subject_groups
        groups = list(_still_vision_required_subject_groups(scene) or [])
    except (ImportError, AttributeError):
        from video.video_downloader import extract_query_anchors
        groups = list(extract_query_anchors(str((scene or {}).get("keyword") or "")) or [])

    normalized = [
        str(group or "").strip().lower()
        for group in groups
        if str(group or "").strip()
    ]
    return tuple(sorted(dict.fromkeys(normalized)))


def _subject_proof_identity(scene, required_groups=None):
    contract = _canonical_still_contract(scene)
    canonical = " ".join(
        str(contract.get("canonical_subject") or "").strip().lower().split()
    )
    discriminators = tuple(sorted(dict.fromkeys(
        str(value or "").strip().lower()
        for value in contract.get("trusted_visual_discriminators") or []
        if str(value or "").strip()
    )))
    required = tuple(sorted(dict.fromkeys(
        str(value or "").strip().lower()
        for value in (required_groups or _subject_proof_required_groups(scene))
        if str(value or "").strip()
    )))
    if not canonical or not required:
        return ()
    return canonical, discriminators, required


def _is_question_subject_beat(scene):
    scene = scene or {}
    role_values = {
        str(scene.get("role") or "").strip().lower(),
        str(scene.get("scene_role") or "").strip().lower(),
        str(scene.get("causal_role") or "").strip().lower(),
    }
    purpose = str(scene.get("semantic_purpose") or "").strip().lower()
    is_question = "question" in role_values or purpose.startswith("question")
    if not is_question:
        return False

    # A question beat may only restate/ask about the already observed subject.
    # Any owned explanatory claim remains ineligible for subject-only reuse.
    causal_role = str(scene.get("causal_role") or "").strip().lower()
    if causal_role in {"mechanism_input", "mechanism_change", "primary_result"}:
        return False
    if str(scene.get("owned_claim_id") or "").strip():
        return False
    required_explanatory = scene.get("required_explanatory_groups") or []
    if isinstance(required_explanatory, dict):
        required_explanatory = [
            key for key, value in required_explanatory.items() if bool(value)
        ]
    if any(str(value or "").strip() for value in required_explanatory):
        return False
    return True


def _cache_verified_subject_proof(scene, *, image_path, source_id, evidence, verified):
    evidence = evidence if isinstance(evidence, dict) else {}
    if not verified or not source_id:
        return False
    if not bool(evidence.get("pass", False)):
        return False
    if not bool(evidence.get("schema_parser_consistency", True)):
        return False
    if evidence.get("obvious_generation_artifact", False):
        return False
    if evidence.get("factual_visual_contradiction", False):
        return False

    required = tuple(sorted(dict.fromkeys(
        str(value or "").strip().lower()
        for value in (evidence.get("required_subject_groups") or [])
        if str(value or "").strip()
    )))
    identity = _subject_proof_identity(scene, required)
    if not identity or not required:
        return False

    raw_groups = {
        str(key or "").strip().lower(): bool(value)
        for key, value in (
            evidence.get("raw_visible_subject_groups")
            or evidence.get("visible_subject_groups")
            or {}
        ).items()
        if str(key or "").strip()
    }
    effective_groups = {
        str(key or "").strip().lower(): bool(value)
        for key, value in (
            evidence.get("effective_subject_groups")
            or evidence.get("visible_subject_groups")
            or {}
        ).items()
        if str(key or "").strip()
    }
    if any(not bool(effective_groups.get(group, False)) for group in required):
        return False
    # Chevron proof must be structured and directly visible; parent-domain or
    # reason-text inference is never sufficient for this feature.
    if "chevron" in required and not bool(raw_groups.get("chevron", False)):
        return False

    _VERIFIED_SUBJECT_PROOF_CACHE[identity] = {
        "image_path": str(image_path),
        "provider": "openai_image",
        "source_id": str(source_id),
        "source_asset_id": str(source_id),
        "canonical_subject": identity[0],
        "trusted_visual_discriminators": list(identity[1]),
        "required_subject_groups": list(identity[2]),
        "raw_visible_subject_groups": dict(raw_groups),
        "effective_subject_groups": dict(effective_groups),
        "visible_components": list(evidence.get("visible_components") or []),
        "schema_parser_consistency": True,
        "verification_status": "PASS",
        "verifier_pass": True,
        "fact_safe": True,
    }
    return True


def _reuse_verified_question_subject(scene, *, output_path, duration, trigger_reason):
    if not _is_question_subject_beat(scene):
        return None
    required = _subject_proof_required_groups(scene)
    identity = _subject_proof_identity(scene, required)
    if not identity:
        return None
    cached = dict(_VERIFIED_SUBJECT_PROOF_CACHE.get(identity) or {})
    if not cached:
        return None
    if str(cached.get("verification_status") or "") != "PASS":
        return None
    if not bool(cached.get("verifier_pass", False)):
        return None
    if not bool(cached.get("schema_parser_consistency", False)):
        return None
    if not bool(cached.get("fact_safe", False)):
        return None
    cached_required = tuple(sorted(
        str(value or "").strip().lower()
        for value in cached.get("required_subject_groups") or []
        if str(value or "").strip()
    ))
    if cached_required != tuple(required):
        return None

    effective_groups = cached.get("effective_subject_groups") or {}
    if any(not bool(effective_groups.get(group, False)) for group in required):
        return None
    raw_groups = cached.get("raw_visible_subject_groups") or {}
    if "chevron" in required and not bool(raw_groups.get("chevron", False)):
        return None

    image_path = Path(str(cached.get("image_path") or ""))
    source_id = str(cached.get("source_id") or "")
    source_asset_id = str(cached.get("source_asset_id") or source_id)
    if not source_id or not image_path.is_file():
        return None
    if not _source_reuse_allowed(source_id, scene):
        return None

    try:
        # No additional Vision call: the exact same physical still already has
        # authoritative structured proof for the exact same canonical subject.
        _motion_clip(image_path, output_path, duration)
        _register_source_use(source_id, scene)
        print(
            f"[QUESTION_SUBJECT_REUSE] scene={_scene_id(scene)} status=reused_verified "
            f"canonical={identity[0]} required={'+'.join(required)} "
            f"source_id={source_id} source_asset_id={source_asset_id} "
            f"source_uses={verified_source_use_count(source_id)} trigger={trigger_reason}"
        )
        return {
            "path": str(output_path),
            "provider": cached.get("provider", "openai_image"),
            "source_id": source_id,
            "source_asset_id": source_asset_id,
            "mode": "REUSED_VERIFIED_QUESTION_SUBJECT_MOTION",
            "tier": 2,
            "visual_state": "TRUE",
            "anchor_matched": len(required),
            "anchor_total": len(required),
            "visible_components": list(cached.get("visible_components") or []),
            "verification_evidence_reused": True,
        }
    except Exception as exc:
        Path(output_path).unlink(missing_ok=True)
        print(
            f"[QUESTION_SUBJECT_REUSE] scene={_scene_id(scene)} status=reuse_failed "
            f"reason={type(exc).__name__}"
        )
        return None
'''


def main():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_PARENT_DOMAIN_PROPAGATION_V1" not in text:
        raise RuntimeError("question subject reuse requires authoritative parent-domain evidence")
    if "STILL_VISION_EVIDENCE_GROUPS_V1" not in text:
        raise RuntimeError("question subject reuse requires structured Vision evidence")

    globals_anchor = '''_VERIFIED_STILL_CACHE = {}\n_VERIFIED_SOURCE_USE_COUNTS = {}\n'''
    globals_replacement = '''_VERIFIED_STILL_CACHE = {}\n_VERIFIED_SOURCE_USE_COUNTS = {}\n_VERIFIED_SUBJECT_PROOF_CACHE = {}\n'''
    if text.count(globals_anchor) != 1:
        raise RuntimeError("question subject reuse globals anchor mismatch")
    text = text.replace(globals_anchor, globals_replacement, 1)

    reset_anchor = '''    _VERIFIED_STILL_CACHE.clear()\n    _VERIFIED_SOURCE_USE_COUNTS.clear()\n'''
    reset_replacement = '''    _VERIFIED_STILL_CACHE.clear()\n    _VERIFIED_SOURCE_USE_COUNTS.clear()\n    _VERIFIED_SUBJECT_PROOF_CACHE.clear()\n'''
    if text.count(reset_anchor) != 1:
        raise RuntimeError("question subject reuse reset anchor mismatch")
    text = text.replace(reset_anchor, reset_replacement, 1)

    helper_anchor = "\ndef _reuse_verified_still(scene, *, output_path, duration, trigger_reason):\n"
    if text.count(helper_anchor) != 1:
        raise RuntimeError("question subject reuse helper anchor mismatch")
    text = text.replace(helper_anchor, _HELPERS + helper_anchor, 1)

    cache_anchor = '''        source_id = f"still-{digest}"\n        signature = _anchor_signature(scene)\n'''
    cache_replacement = '''        source_id = f"still-{digest}"\n        _cache_verified_subject_proof(\n            scene,\n            image_path=image_path,\n            source_id=source_id,\n            evidence=evidence,\n            verified=verified,\n        )\n        signature = _anchor_signature(scene)\n'''
    if text.count(cache_anchor) != 1:
        raise RuntimeError("question subject reuse verified-cache anchor mismatch")
    text = text.replace(cache_anchor, cache_replacement, 1)

    reuse_anchor = '''    reused = _reuse_verified_still(\n        scene,\n        output_path=output_path,\n        duration=duration,\n        trigger_reason=trigger_reason,\n    )\n'''
    reuse_replacement = '''    question_reused = _reuse_verified_question_subject(\n        scene,\n        output_path=output_path,\n        duration=duration,\n        trigger_reason=trigger_reason,\n    )\n    if question_reused:\n        return question_reused\n\n''' + reuse_anchor
    if text.count(reuse_anchor) != 1:
        raise RuntimeError("question subject reuse dispatch anchor mismatch")
    text = text.replace(reuse_anchor, reuse_replacement, 1)

    path.write_text(text, encoding="utf-8")
    print("✅ Run 33371268494 question-beat verified subject reuse installed")


if __name__ == "__main__":
    main()
