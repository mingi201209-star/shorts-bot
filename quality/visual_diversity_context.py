from contextlib import contextmanager

_EXCLUDED_PHYSICAL_ASSET_IDS = set()


def normalize_physical_asset_id(value):
    return str(value or "").strip().lower()


def is_physical_asset_excluded(asset_id):
    return normalize_physical_asset_id(asset_id) in _EXCLUDED_PHYSICAL_ASSET_IDS


@contextmanager
def excluded_physical_assets(asset_ids):
    added = {normalize_physical_asset_id(x) for x in (asset_ids or set()) if normalize_physical_asset_id(x)}
    previous = set(_EXCLUDED_PHYSICAL_ASSET_IDS)
    _EXCLUDED_PHYSICAL_ASSET_IDS.update(added)
    try:
        yield
    finally:
        _EXCLUDED_PHYSICAL_ASSET_IDS.clear()
        _EXCLUDED_PHYSICAL_ASSET_IDS.update(previous)
