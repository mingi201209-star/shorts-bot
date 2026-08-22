# Analytics feedback contract

This package stores observational lineage for a produced Short:

`candidate -> hook -> script -> production -> publication -> delayed performance`

It deliberately does not change Candidate Explorer or production policy. Missing analytics remain `None` with an explicit snapshot collection state; numeric zero is a real observed value.

The 24-hour and 72-hour snapshots are independent so downstream growth experiments can consume the strongest available evidence without treating uncollected data as failure.
