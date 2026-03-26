# Blackbox Evidence Ledger and Delay-Tolerant Sync Queue

This commit adds the last major subsystem layer before final validation and repo
presentation: a tamper-evident blackbox evidence ledger plus a deterministic
delay-tolerant sync queue.

That matters because the savage pain point is not only local triage. It is also
preserving what happened onboard so later ground review does not rely on vague
memories or half-trusted telemetry scraps.

## Blackbox Evidence Ledger

The ledger is append-only and chain-hashed.

Each record carries:

- `record_index`
- `record_type`
- `time_s`
- `previous_hash`
- `record_hash`
- `payload`

The chain starts from a deterministic genesis state and records:

- scenario contract snapshot
- replay summary
- replay events
- sentinel report
- triage report
- gate report

## Why the Ledger Exists

It gives DSAT a bounded answer to:

- what did the subsystem ingest?
- what did it infer?
- what did it allow or block?
- what evidence chain ties those together?

That is blackbox value, even before any real flight integration.

## Delay-Tolerant Sync Queue

The sync queue packages ledger records into deterministic store-and-forward
envelopes for later export when contact opportunities reopen.

This commit does **not** implement real networking.

It does implement:

- priority ordering
- manifest hashing
- bounded envelope sizing
- deterministic packaging

## Current Priorities

The queue currently uses four levels:

- `critical`
- `high`
- `normal`
- `low`

Critical records include gate decisions and anomaly posture changes first.

## Why This Matters

A delayed-ground mission cannot assume continuous bulk transfer.

So DSAT should be able to say:

- which evidence is most urgent?
- what can be sent first?
- what chain head does that evidence belong to?
- what manifests prove packaging order?

That is what this module starts answering.

## CLI Usage

Build a ledger summary:

```bash
ix-dsat --ledger-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

Build a sync-queue summary:
ix-dsat --sync-queue-scan scenarios/examples/link_state_pointing_drift.json --sample-every 10

The outputs are compact JSON summaries with:

ledger chain head
record count
record types
sync envelope count
sync priorities
manifest hashes
