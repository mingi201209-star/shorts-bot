import video.still_image_fallback as stills


def run():
    stills.reset_still_image_budget()
    scene = {"role": "mechanism", "keyword": "aircraft wing", "text": "test"}
    source = "still-fixture-a"

    assert stills._source_reuse_allowed(source, scene) is True
    stills._register_source_use(source, scene)
    assert stills.verified_source_use_count(source) == 1
    assert stills._source_reuse_allowed(source, scene) is True
    stills._register_source_use(source, scene)
    assert stills.verified_source_use_count(source) == 2
    assert stills._source_reuse_allowed(source, scene) is False

    # Non-information atmosphere reuse remains outside the hard information budget.
    atmosphere = {"role": "atmosphere", "keyword": "aircraft wing"}
    assert stills._source_reuse_allowed(source, atmosphere) is True

    # A distinct qualified physical still begins with its own supply budget.
    second = "still-fixture-b"
    assert stills._source_reuse_allowed(second, scene) is True
    stills._register_source_use(second, scene)
    assert stills.verified_source_use_count(second) == 1

    # Production budgets and create_scene contract are not changed by this module.
    assert stills.STILL_IMAGE_MAX_PER_VIDEO == 2
    assert stills.MAX_INFORMATION_USES_PER_PHYSICAL_STILL == 2
    print("VISUAL_SUPPLY_V1_REGRESSION_PASS")


if __name__ == "__main__":
    run()
