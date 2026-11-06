# Streaming the record as it is written

A run may send each receipt to a console as it is written, so the console can show the run filling
in step by step while it is still going. Streaming **shares the record as it grows; it is not the
record.**

## Turning it on

```python
@ot.run(stream_to="https://console.example/ingest")
def main():
    ...
```

or set `ONETRACE_STREAM_TO` in the environment, so a deployment can turn it on without changing the
code. `Recorder(stream_to=…)` does the same.

## What is sent

As each receipt is written, its bytes are sent to the endpoint as an HTTP POST. The body is the
receipt's bytes and nothing else; the run id and the receipt's position in the chain (its index and
digest) travel as headers (`X-Onetrace-Run-Id`, `X-Onetrace-Chain-Index`, `X-Onetrace-Chain-Digest`).

Streaming **changes no receipt and adds nothing to the chain.** A run streamed and a run not
streamed write the same receipts and the same chain head; the only difference is in the manifest,
which records the stream's outcome.

## When the endpoint cannot be reached

A slow or dead endpoint never holds the run up. The receipt is written, the chain goes on, and the
stream for that receipt is recorded as not delivered. When the run closes, the manifest says how
many receipts were delivered and how many were not:

```json
"stream": {"delivered": "3", "not_delivered": "2", "note": "the stream was not delivered"}
```

The endpoint URL is not recorded. A failed stream changes no receipt: the run records as before and
verifies as before.

## The other mode: watching the folder

A console on the same machine can instead watch the run folder and read each receipt as it appears;
there is nothing to configure in the SDK for that. Streaming is for a console that is not on the
machine the run is on.

## What streaming does not claim

- Streaming shares the record as it grows; it is not the record. Only the written run folder, read
  and verified, is the record.
- A receipt that reached a console is provisional until the run closes and its whole chain verifies.
