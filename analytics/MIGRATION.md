# Legacy normalization

Older records may not contain analytics fields. `normalize_video_lineage()` adds the current additive fields and initializes absent 24h/72h snapshots as `pending`; it does not convert missing values to zero.
