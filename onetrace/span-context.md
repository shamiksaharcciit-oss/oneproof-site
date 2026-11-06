# The span context

When a step runs inside an active OpenTelemetry span, its receipt records that span's W3C trace id
and span id, and the run's manifest records the run's own `traceparent`. This is the one thing the
record keeps about a trace: where the run and its steps ran, so a later reader can line the record
up with the spans an app emitted — nothing more.

## What is read, and from where

- Where an OpenTelemetry package is installed and a span is recording, its active span is read.
- Where none is, the `TRACEPARENT` environment variable is read instead.
- With no active span and no `TRACEPARENT`, nothing is recorded and the receipt is byte-identical
  to 0.4.0.

No OpenTelemetry package is required: onetrace reads the active context where it can and the environment
otherwise. No network call is made.

## What is recorded

- Each step's receipt gets an optional `trace` block: `{"trace_id": "<32 hex>", "span_id":
  "<16 hex>"}`, the span active when the step ran.
- The run's manifest gets an optional `traceparent`: the full W3C traceparent the run ran in
  (`00-<32 hex trace id>-<16 hex span id>-<2 hex flags>`).

A `TRACEPARENT` that is present but malformed — not a W3C traceparent, or with an all-zero id — is
refused and named, never recorded: a broken trace is not written into the record.

## What this does not claim

- **A trace is a view, not evidence.** It may be sampled, dropped, rewritten or re-timed by a
  collector. The span context says which trace the run and its steps ran in; only the record proves
  the step's inputs and outputs.
