#!/usr/bin/env python3


def normalize_dispatch_input(value):
    """Serialize a workflow_dispatch scalar without changing non-bool semantics."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if not isinstance(value, (str, int, float)) and value is not None:
        raise ValueError("dispatch input must be a scalar value")
    return "" if value is None else str(value)
