"""Clean V2 exact-asset scene renderer.

This module reuses V1's low-level TTS/video/subtitle primitives but never calls
create_scene() and never performs provider search.  The only video source it is
allowed to download is CandidateVisualV2.media_url that already passed V2 QA.
"""

from __future__ import annotations

import os
import shutil
from typing import Any, List

from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2


def create_scene_from_selected_visual(
    idx: int,
    scene: SceneV2,
    plan: VisualPlanV2,
    visual: CandidateVisualV2,
    *,
    create_voice_fn=None,
    get_scene_paths_fn=None,
    download_video_fn=None,
    prepare_vertical_video_fn=None,
    load_video_for_scene_fn=None,
    create_subtitle_clips_fn=None,
    audio_clip_cls=None,
    composite_clip_cls=None,
):
    """Build one scene from the exact accepted asset. No search is possible."""
    if not visual.media_url.strip():
        raise ValueError(
            f"V2 selected visual for scene {scene.scene_index} has no media_url"
        )

    if create_voice_fn is None:
        from integrations.tts import create_voice as create_voice_fn
    if get_scene_paths_fn is None or prepare_vertical_video_fn is None or load_video_for_scene_fn is None:
        from video.video_engine import (
            get_scene_paths,
            load_video_for_scene,
            prepare_vertical_video,
        )
        get_scene_paths_fn = get_scene_paths_fn or get_scene_paths
        prepare_vertical_video_fn = prepare_vertical_video_fn or prepare_vertical_video
        load_video_for_scene_fn = load_video_for_scene_fn or load_video_for_scene
    if download_video_fn is None:
        from video.video_downloader import download_video as download_video_fn
    if create_subtitle_clips_fn is None:
        from video.subtitle_engine import create_subtitle_clips as create_subtitle_clips_fn
    if audio_clip_cls is None or composite_clip_cls is None:
        from moviepy.editor import AudioFileClip, CompositeVideoClip

        audio_clip_cls = audio_clip_cls or AudioFileClip
        composite_clip_cls = composite_clip_cls or CompositeVideoClip

    paths = get_scene_paths_fn(idx)
    audio_path = paths["audio"]
    source_video_path = paths["source_video"]
    vertical_video_path = paths["vertical_video"]

    print(
        "[V2_EXACT_ASSET] "
        f"scene={scene.scene_index} provider={visual.provider or 'unknown'} "
        f"source_id={visual.source_id or 'unknown'}"
    )

    create_voice_fn(scene.narration, audio_path)
    if not os.path.exists(audio_path):
        raise RuntimeError(f"TTS file missing: {audio_path}")

    audio_clip = None
    video_clip = None
    try:
        audio_clip = audio_clip_cls(audio_path)
        duration = float(audio_clip.duration or 0)
        if duration <= 0:
            raise RuntimeError("TTS duration is zero")

        # Future generated providers may hand V2 a local file. Stock providers
        # hand it a remote URL. Both preserve the exact accepted asset identity.
        if os.path.isfile(visual.media_url):
            shutil.copyfile(visual.media_url, source_video_path)
        else:
            download_video_fn(visual.media_url, source_video_path)

        if not os.path.exists(source_video_path):
            raise RuntimeError(f"selected visual download missing: {source_video_path}")

        prepare_vertical_video_fn(
            source_video_path,
            vertical_video_path,
            duration,
        )
        if not os.path.exists(vertical_video_path):
            raise RuntimeError(f"vertical scene missing: {vertical_video_path}")

        video_clip = load_video_for_scene_fn(vertical_video_path, duration)
        subtitle_clips = create_subtitle_clips_fn(
            scene.narration,
            duration,
            video_clip=video_clip,
            hook_mode=(idx == 0),
        )
        combined = composite_clip_cls(
            [video_clip, *subtitle_clips],
            size=(1080, 1920),
        )
        return combined.set_audio(audio_clip).set_duration(duration)
    except Exception:
        if video_clip is not None:
            try:
                video_clip.close()
            except Exception:
                pass
        if audio_clip is not None:
            try:
                audio_clip.close()
            except Exception:
                pass
        raise


def generate_selected_scenes(
    scenes: List[SceneV2],
    plans: List[VisualPlanV2],
    visuals: List[CandidateVisualV2],
    *,
    create_scene_fn=create_scene_from_selected_visual,
) -> List[Any]:
    if not (len(scenes) == len(plans) == len(visuals)):
        raise ValueError(
            "V2 exact-asset render inputs must align: "
            f"{len(scenes)}/{len(plans)}/{len(visuals)}"
        )

    clips = []
    try:
        for idx, (scene, plan, visual) in enumerate(zip(scenes, plans, visuals)):
            clips.append(create_scene_fn(idx, scene, plan, visual))
        return clips
    except Exception:
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass
        raise
