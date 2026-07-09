---
name: Advisory lock keys must be deterministic
description: pg_advisory_lock key derivation must not use Python's built-in hash() — it breaks cross-process locking silently
---

Postgres advisory locks (`pg_advisory_lock` / `pg_advisory_xact_lock`) take an
integer key. If that key is derived from a string (e.g. a SKU code) using
Python's built-in `hash()`, the lock silently stops working across processes:
`hash()` on strings is randomized per-process via `PYTHONHASHSEED` (a security
mitigation, on by default since Python 3.3), so the same string produces a
different integer in every process. Two processes intending to serialize on
the same logical resource end up locking on two different, uncorrelated keys
— no error, no exception, just a lock that never actually contends.

**Why:** Found in Oracare's lot-reservation system — a lock meant to prevent
two processes from over-reserving the last units of a lot used `hash(sku)` as
the advisory lock key. It worked fine in any single-process test but provided
zero real protection in production where the webhook handler and the
scheduled reconciliation sweep run as separate processes.

**How to apply:** Any time an advisory lock key (or any other cross-process
identity derived from hashing) is built from a string, use a stable hash —
`hashlib.sha256(s.encode()).hexdigest()` truncated/converted to an int, `zlib.crc32`,
or similar — never the built-in `hash()`. Verify by comparing the derived key
across two separate `python3 -c "..."` invocations, not just within one
process/test run.
