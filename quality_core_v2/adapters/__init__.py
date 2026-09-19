"""LLM/provider-calling adapters for the Clean V2 pipeline.

Every module here is split into two halves on purpose:

1. A pure function (`parse_*` / `*_from_provider_hit`) that turns an
   already-received API response into a typed quality_core_v2.schemas
   object. Zero I/O. Fully covered by adapters_test.py with canned
   fixtures -- no network, no API key required to test this half.
2. A thin call function (`call_*`) that does the actual network/LLM call
   and then hands the raw response to the pure function above. This half
   cannot be exercised in this session (no OPENAI_KEY / PEXELS_API_KEY
   available here) and is untested by adapters_test.py; it is only
   exercised for real inside GitHub Actions, where those secrets exist.

This split is what keeps the replay harness's "0 network calls" property
intact while still letting real generation code live in this package.
"""
