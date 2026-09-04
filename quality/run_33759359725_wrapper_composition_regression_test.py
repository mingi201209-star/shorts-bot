"""Regression for production Run 33759359725 choose_best_candidate wrapper recursion.

This test is intended to run only after the production hotfix installer sequence has
been applied to a clean checkout. It detects cyclic predecessor bindings without
calling any external API, then verifies the composed selector can terminate on an
empty candidate set.
"""
from __future__ import annotations

import importlib
import sys


MAX_WRAPPER_DEPTH = 64
PREDECESSOR_SUFFIX = "previous_choose_best_candidate"


def _previous_wrapper(fn):
    names = [
        name
        for name in fn.__code__.co_names
        if name.endswith(PREDECESSOR_SUFFIX)
    ]
    if not names:
        return None, None
    if len(names) != 1:
        raise AssertionError(
            f"ambiguous choose_best_candidate predecessor bindings for {fn.__name__}: {names}"
        )
    name = names[0]
    previous = fn.__globals__.get(name)
    if not callable(previous):
        raise AssertionError(f"missing callable predecessor binding: {name}={previous!r}")
    return name, previous


def _assert_acyclic_wrapper_chain(root):
    seen = {}
    chain = []
    current = root

    for depth in range(MAX_WRAPPER_DEPTH):
        current_id = id(current)
        if current_id in seen:
            cycle_start = seen[current_id]
            rendered = " -> ".join(chain + [current.__name__])
            raise AssertionError(
                "choose_best_candidate wrapper cycle detected: "
                f"cycle_start={cycle_start} chain={rendered}"
            )
        seen[current_id] = depth
        chain.append(current.__name__)

        predecessor_name, previous = _previous_wrapper(current)
        if previous is None:
            return chain
        chain[-1] = f"{current.__name__}[{predecessor_name}]"
        current = previous

    raise AssertionError(
        f"choose_best_candidate predecessor chain exceeded {MAX_WRAPPER_DEPTH}: "
        + " -> ".join(chain)
    )


def main():
    sys.modules.pop("video.video_downloader", None)
    downloader = importlib.import_module("video.video_downloader")

    assert "RUN_33691170895_DISCRIMINATIVE_SUBJECT_GUARD_V1" in open(
        "video/video_downloader.py", encoding="utf-8"
    ).read()
    assert "FINAL_VISUAL_SELECTION_LINEAGE_V1" in open(
        "video/video_downloader.py", encoding="utf-8"
    ).read()

    chain = _assert_acyclic_wrapper_chain(downloader.choose_best_candidate)
    print("WRAPPER_CHAIN=" + " -> ".join(chain))

    try:
        result = downloader.choose_best_candidate(
            [],
            relevant_top_n=None,
            historical=False,
            subject_filter_query=None,
        )
    except RecursionError as exc:
        raise AssertionError(
            "authority counterexample reproduced: choose_best_candidate recursed after "
            "production hotfix composition"
        ) from exc

    assert result is None, result
    print("RUN_33759359725_WRAPPER_COMPOSITION=PASS")


if __name__ == "__main__":
    main()
