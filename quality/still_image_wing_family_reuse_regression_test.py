from video import still_image_fallback as fallback


def main():
    wing = {"keyword": "aircraft wing vortex during flight stage 9"}
    winglet = {"keyword": "aircraft wing winglet action stage 10"}
    window = {"keyword": "aircraft window shade stage 4"}

    assert fallback._anchor_signature(wing) == ("aircraft", "wing")
    assert fallback._anchor_signature(winglet) == ("aircraft", "winglet")
    assert fallback._reuse_signatures(wing) == (
        ("aircraft", "wing"),
        ("aircraft", "winglet"),
        ("aircraft", "wingtip"),
    )
    assert fallback._reuse_signatures(winglet) == (("aircraft", "winglet"),)
    assert ("aircraft", "wing") not in fallback._reuse_signatures(winglet)
    assert ("aircraft", "winglet") not in fallback._reuse_signatures(window)
    print("STILL IMAGE WING-FAMILY REUSE REGRESSION: PASS")


if __name__ == "__main__":
    main()
