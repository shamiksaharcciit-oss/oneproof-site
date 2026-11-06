# The model-call record

A **model-call record** is one canonical JSON document per model call, written as an ordinary output
of the stage that made the call. It is evidence beside the stage receipt: it never changes the
receipt format and never adds a member to the receipt or the chain. It never changes the reading of a
run's receipts; its own verifier rows read as every other row does, and a FAIL on one fails the run
like any other FAIL. A run that writes no record is byte-for-byte the run it would be without the
feature.

It is written by `onetrace.model_call`, installed with `onetrace[model-call]`. The engine adapters
import vLLM or transformers only when used, so the engine stays your own installed version; onetrace
pins no engine. The transformers adapter is tested only where torch and transformers are installed
(`tests/test_model_call_capture.py`, a tiny model built from a config on the CPU); its tests skip
without them. CI runs them in a job of their own on a CPU-only torch, pinned by hash. The record's schema is `docs/model_call_record.schema.json`, labelled
`model-call-record/1.0`.

## What a record holds, and how honestly

Every scalar in a record is a string. Every field that describes the call is a **value object** with a
`status`, a `source`, and — where there is one — a `value`. A field the writer cannot fill is written
as `not observed` or `not applicable`, with its reason in `source`: never left out, and never given a
default.

The five states:

- **`observed`** — read at call time; `source` says from where.
- **`declared, not observed`** — given by the caller and not read back from the engine; `source` says
  what it is.
- **`declared, contradicted`** — declared, and a different value was read; both are kept (`value` the
  declaration, `observed_value` the reading).
- **`not observed`** — the writer cannot see it; no value, never a default; `source` says so.
- **`not applicable`** — the field has no meaning for this engine or call; no value; `source` says
  why.

Four fields are written by the helper itself, as plain strings with no state — they describe how the
record was written, not the call: `format`, `call.kind`, `call.api`, and `credential`.
`credential` is `present` or `absent` — never the key, its digest, or any part of it.

### The record says only what it observed

The record is written so that a status is never a claim the writer did not make:

- **Settings the engine did not expose are declared, not observed.** A self-hosted call's
  `sampling.*` is the caller's own sampling parameters as built, not read back from the engine, so it
  is `declared, not observed`. A value a caller hands the adapter for a `runtime.*` field is
  `declared, not observed` for that field — never shown as observed.
- **The runtime is read in the calling process.** `runtime.torch`, `runtime.cuda`,
  `runtime.gpu_name` and `runtime.compute_capability` are read from `torch` in the calling process
  and are `observed` from it; a field not read there is `not observed`. The driver is not read from
  `torch`: a driver the caller gives the adapter is `declared, not observed`, as a caller's value for
  any `runtime.*` field is; without one, the driver is `not observed`; it is never `observed`. On a CPU run, the transformers adapter writes the GPU runtime fields
  (`runtime.cuda`, `runtime.gpu_name`, `runtime.compute_capability`, `runtime.driver`) as **`not
  applicable`** — `not applicable` is one of the record's five states, and it is the truer word than
  `not observed` for a field that has no meaning on a CPU run.
- **A model digest names the directory it hashed, not the engine.** `model.files_digest` and
  `tokenizer.digest` are the digest of the directory given to the adapter; the `source` says "the
  directory given to the adapter; not read from the engine." Nothing ties the hashed directory to the
  weights the engine actually loaded, and the record does not claim it does.
- **A self-hosted record digests the output text only where there is one.** vLLM's
  `output.text_digest` is read from the engine's own setting, `model_config.skip_tokenizer_init`.
  With it on, the engine produces no text, and the member is `not applicable`. With it off, it is
  `observed`: the sha256 of `RequestOutput.outputs[0].text`'s UTF-8 bytes. The record holds the
  digest, never the text. A setting that cannot be read leaves the member `not observed`.
- **A constant says it is a constant.** `engine.name` is `observed` with the source "a constant
  written by this adapter."
- **The filler count is the caller's.** `batch.fillers` is `declared, not observed`: how many of the
  submitted requests the caller said were fillers.
- **A hosted call invents nothing.** Every internal field of a hosted call (`engine.*`, `runtime.*`,
  `batch.*`, the token-id digests) is `not observed`: the provider does not expose it. When the
  request names no model, `model.requested` is `not observed`, "the request names no model" — not an
  empty declared string. On an HTTP error, `output.finish` is `observed`, `error (HTTP <status>)`,
  with the source "the response's HTTP status": the status is what was observed, not a finish reason
  the provider did not send.

### The fingerprints

`fingerprints` is a list of distribution digests. A transformers prefill records an `exact` form (the
raw bytes of the last position's logits) and a `tolerant` form (the top-16 token ids of that
position, rounded). A vLLM call records a `topk_exact` and a `tolerant` form over the first generated
token's top-16 log-probabilities. A hosted call records a `tolerant` form over the provider's
first-token log-probabilities, when the response carries at least 16.

A vLLM request that delivered no token has no first-token log-probabilities, and the vLLM
fingerprint has no value defined for it. A 1.1 record writes both forms `not observed`, with the
source `RequestOutput.outputs[0] holds no generated token: no first-token log-probabilities to
digest`. A call with no capture still stops at such a request with an `IndexError`, as onetrace
0.6.1 does.

## Several calls in one stage

The first record a stage writes is `model_call.json`, then `model_call.2.json`, `model_call.3.json`,
and so on, in write order. The package refuses a name it has already used in a stage before it writes,
so a repeat never reaches onetrace.

## The capture levels, and the steps file

A call's **answer** — its chosen token ids — is the model's own output, not the operator's. The
record never holds a token id or any text, at any capture level.

When a per-step capture (L1: the chosen token ids; L2: the top-k candidate ids) is taken, it is
written as a **separate output**, `model_call.<n>.steps.json`, classed **`model-generated`**, and the
record names it only by **digest**, in the optional `steps` field. The token ids live in that
model-generated file; the operator-authored record holds a digest of it and nothing more.

A prefix-digest chain over the token ids is not a way to hide them: each step's digest, with the
model's vocabulary, **reveals the tokens to anyone with the vocabulary**. The steps file is treated as
the model's output, classed `model-generated`, for that reason.

The cost of taking L1 or L2 is **not measured**. L3 (a full per-step capture on the serving engine) is
**not measured**.

## `model-call-record/1.1`: the self-hosted steps file, from onetrace 0.7

This section gives six parts of `model-call-record/1.1` for a self-hosted call, from
`design/model_call_l3.md` and vLLM 0.30.0's source. This build writes 1.1 for a self-hosted vLLM call
captured at L1, L2 or L3: `capture.vllm`'s `Engine.generate(..., level=..., ctx=...)` writes each
request's steps file and its record through the stage context. A call with no capture is written as
1.0, as before. onetrace-verify before 0.7 does not check a 1.1 record's content (`docs/format.md`). **The record
format is not part of the Internet-Draft**: the draft describes the receipt and its chain, and the
record formats sit outside it, as `design/format_04_members.md` says.

### The steps file at L1, L2 and L3

`model_call.<n>.steps.json`, classed `model-generated`, as in 1.0: one JSON object, written
canonically.

| Member | Type | L1 | L2 | L3 |
|---|---|---|---|---|
| `level` | string | `"L1"` | `"L2"` | `"L3"` |
| `method` | string | `"token-ids"` | `"top-k-ids"` | `"sha256-tree-512/v0"` |
| `token_ids` | list of decimal strings | yes | yes | yes |
| `top_k_ids` | list of lists of decimal strings | — | yes | yes |
| `digests` | list of 64-character lowercase hex strings | — | — | yes |

- **No other member, at any level.** `level` and `method` equal the record's `steps.level` and
  `steps.method`. L3 is L2 plus the digests.
- **Step i is the i-th delivered token,** counted from 0. `token_ids[i]` is the id the engine chose
  at step i; `top_k_ids[i]` the ids ranked 1 to k at step i, by the engine's own rank, rank 1 first,
  with the chosen id kept in `token_ids[i]` alone; `digests[i]` the `sha256-tree-512/v0` digest of
  the row the engine chose `token_ids[i]` from.
- **Every list has exactly `steps.count` entries,** and `steps.count` is `len(token_ids)`.
  `top_k_ids[i]` holds between `steps.k_returned_min` and `steps.k_returned_max` ids, never padded,
  never empty, with no id twice.
- **Ids are decimal strings:** base 10, no sign, no leading zero, `"0"` for zero. The steps file is
  written through `ctx.write_json`, which refuses a JSON number anywhere.
- **L3's digests: exactly one per delivered token.** A capture that holds fewer digests than delivered
  tokens writes no steps file. The record then carries `steps.level` `declared, not observed`, value
  `L3`, and `steps` `not observed`, with the source `the capture held <n> digests for <m> delivered
  tokens`, and no other `steps.*` member. So it has no `steps.k_*` member and no steps file. A
  verifier reads its `steps.k_*` members as NOT-RUN with that reason, beside `no capture taken` for
  a record with no capture, and its steps file as NOT-RUN, `the steps file was not written`.
- **At L1, and at `L1-hosted`,** `steps.k_requested`, `steps.k_returned_min` and
  `steps.k_returned_max` are each `not applicable`, with the source `<level> holds no candidates`,
  never left out. L3's missed-digest record, above, holds none of the three.
- **No `steps.logprobs`.** A self-hosted record does not carry `steps.logprobs`, at any level: L2 and
  L3 carry ids, not probabilities.
- **A request with no delivered token** is a record like any other. Its `steps.count` is `"0"`, and
  its steps file holds the level's members with every list empty. At L2 and L3,
  `steps.k_returned_min` and `steps.k_returned_max` are each `not applicable`, with the source `no
  step: the request delivered no token`; `steps.k_requested` is written as at any other count. At
  L3, `steps.surplus` counts every digest the capture took for it. `output.finish` is as read, and
  both fingerprints are `not observed` (the fingerprints, above).

### The record's `steps.*` members

The record's `format` is `model-call-record/1.1` wherever these members are written. A 1.0 record
holding one of them is outside its format.

| Member | State | Source | Value |
|---|---|---|---|
| `steps` | `observed` | the steps file's name, `model_call.<n>.steps.json` | the file's `sha256:<hex>` |
| `steps.level` | `observed` | `the capture this adapter wrote` | `L1`, `L2`, `L3` |
| `steps.method` | `observed` | `the capture this adapter wrote` | `token-ids`, `top-k-ids`, `sha256-tree-512/v0` |
| `steps.count` | `observed` | `len(RequestOutput.outputs[0].token_ids)` | a decimal string |
| `steps.k_requested` | `declared, not observed`, at L2 and L3 | `SamplingParams.logprobs as the caller built it, not read back from the engine` | the request's `logprobs`, so k is never more than `sampling.logprobs` |
| `steps.k_returned_min`, `steps.k_returned_max` | `observed`, at L2 and L3; `not applicable` at `steps.count` `"0"` | `RequestOutput.outputs[0].logprobs: the ids ranked 1 to k at each step`; at `"0"`, `no step: the request delivered no token` | the fewest and the most ids any step holds |

`top_k_ids[i]` is the ids vLLM ranks 1 to k at step i. The entry vLLM adds for the sampled token
when its rank is outside the top k is left out.

### Where L3's digests are taken

- **L3's own logits processor.** `capture.vllm.start(level="L3", ...)` adds it to the engine's
  `logits_processors`, after any the caller gives. It reports `is_argmax_invariant()` `False`, so vLLM
  calls it at every decoding step, greedy decoding included, and that call is where the digests are
  taken. For each tagged request it digests the float32 row with `sha256-tree-512/v0`, and it never
  changes the logits.
- **Each request is tagged.** The adapter gives each request of the call a copy of its
  `SamplingParams` whose `extra_args` carry a tag of its own; the caller's own `SamplingParams` are
  unchanged. A filler is not tagged, and not digested.
- **The batch is followed by index,** as vLLM reports it to the processor before each step: removals,
  then additions, then moves. A request moved onto another's index takes it.
- **The rows are copied to the host and digested there.** No GPU kernel ships in this build.
- **The digests reach the adapter only where the engine core runs in the calling process.** The
  processor keeps them in the process it runs in, and the adapter reads them in its own. vLLM 0.30.0
  runs the engine core in a separate process by default (`VLLM_ENABLE_V1_MULTIPROCESSING`, on unless
  set to `0`), so `capture.vllm.start(level="L3", ...)` sets it to `0` (below, the engine core). An
  engine whose engine core or workers run in another process anyway is refused at L3.

### `steps.surplus`

- A value object, `observed`, source `digests computed ahead of the request's end and discarded`; its
  value a decimal string: the digests the capture computed for the request, less `len(token_ids)`.
- **`"0"`** at an L3 capture that computed none beyond the delivered tokens: written, not left out.
- **Absent** at L1, L2, `L1-hosted` and `L2-hosted`; with no capture; and where an L3 capture's
  `steps` is `not observed`.
- **Counted, never listed.** No surplus digest is written anywhere, so none can be compared.

### The model runner

`engine.settings.model_runner`, an engine setting under the open `engine.settings.` prefix, values
`V1` and `V2`:
- **The pin.** vLLM 0.30.0 runs the V2 model runner by default, and reads `VLLM_USE_V2_MODEL_RUNNER`
  when the engine starts. `capture.vllm.start(level="L3", ...)` sets it to `0` before it starts the
  engine.
- **The read-back** is the engine configuration's `use_v2_model_runner`, a property vLLM computes
  when it is read. The adapter reads it in the calling process; the worker's own reading is not
  exposed.
- **At L3, on an engine `start` pinned,** its value is `V1`. It is `observed` when read back, source
  `the engine's configuration, read after start in the calling process; pinned to V1 by the
  adapter: L3 asked for`. It is `declared, not observed` when it cannot be read back, source `pinned
  to V1 by the adapter: L3 asked for; not read back from the engine`.
- **Otherwise** it is written as read, source `the engine's configuration, read after start in the
  calling process; not pinned by the adapter`, or `not observed` when it is not read.

### The engine core

`engine.settings.engine_core`, an engine setting under the open `engine.settings.` prefix, values
`in the calling process` and `in another process`:
- **The setting.** vLLM 0.30.0 runs the engine core in a process of its own by default, and reads
  `VLLM_ENABLE_V1_MULTIPROCESSING` when the engine starts. `capture.vllm.start(level="L3", ...)`
  sets it to `0` before it starts the engine, as it sets the runner pin.
- **The read-back** is the class of the engine's `llm_engine.engine_core`, the engine-core client:
  `InprocClient` builds the engine core in the calling process, and `MPClient` and its subclasses
  run it in another.
- **At L3, on an engine `start` set,** its value is `in the calling process`. It is `observed` when
  read back, source `the class of llm.llm_engine.engine_core, read after start in the calling
  process; set to run in the calling process by the adapter: L3 asked for`. It is `declared, not
  observed` when it cannot be read back, source `set to run in the calling process by the adapter:
  L3 asked for; not read back from the engine`.
- **Otherwise** it is written as read, source `the class of llm.llm_engine.engine_core, read after
  start in the calling process; not set by the adapter`, or `not observed` when it is not read.
- **What running the engine core in the calling process costs in speed is not measured.**

### The executor

`engine.settings.executor`, an engine setting under the open `engine.settings.` prefix: the
engine's `parallel_config.distributed_executor_backend` as vLLM resolved it, `uni`, `mp`, `ray`,
`external_launcher`, or a class given as `<module>.<qualname>`.
- **Written at every 1.1 level,** `observed`, source `vllm_config.parallel_config.distributed_executor_backend,
  read after start in the calling process; not set by the adapter`; `not observed`, source `not read
  from the engine's configuration; not set by the adapter`, where there is none to read.
- **vLLM resolves it when the engine is configured:** with no executor given, `uni` at world size 1,
  where world size is pipeline × tensor × prefill-context parallel size; above 1, on a GPU host, `mp`
  or `ray`. `uni` builds the engine's worker in the calling process.
- **The executor as built,** `engine.settings.executor_built`, beside it at every 1.1 level: the class
  of the engine's `llm_engine.model_executor`, read back. vLLM's own classes read as the name they
  are configured by, each by its exact class: `UniProcExecutor` `uni`, `ExecutorWithExternalLauncher`
  `external_launcher` (a subclass of `UniProcExecutor`, and not `uni`), `MultiprocExecutor` `mp`,
  `RayDistributedExecutor` and `RayExecutorV2` `ray`. Any other class reads as `<module>.<qualname>`.
  It is `observed`, source `the class of llm.llm_engine.model_executor, read after start in the
  calling process; not set by the adapter`, or `not observed`, source `not read back from the engine:
  llm.llm_engine.model_executor is not there; not set by the adapter`. vLLM sets it only with the
  engine core in the calling process.

### How the request ended

`output.finish`, the member 1.0 already has. For a self-hosted vLLM record at 1.1 its value is one
of seven:

| Value | Read from |
|---|---|
| `eos` | `finish_reason` `stop`, `stop_reason` none, or a token id that is one of the model's eos token ids and not one of the caller's `stop_token_ids` |
| `stop-string` | `finish_reason` `stop`, `stop_reason` a string |
| `stop-token` | `finish_reason` `stop`, `stop_reason` any other token id |
| `length` | `finish_reason` `length` |
| `abort` | `finish_reason` `abort` |
| `repetition` | `finish_reason` `repetition` |
| `error` | `finish_reason` `error` |

- **State `observed`,** source `RequestOutput.outputs[0].finish_reason and stop_reason`. For a token-id
  `stop_reason`, the source goes on to say whether the id is an eos token id, and where the eos ids
  were read.
- **The model's eos token ids** are read once per engine, from the engine's own configuration: the
  generation config's `eos_token_id`, one id or a list, as the engine read it when it started
  (`llm.llm_engine.input_processor.generation_config_fields`), and the HF config's
  (`model_config.hf_config.eos_token_id`) where the generation config gives none. On an engine
  started with `skip_tokenizer_init`, vLLM 0.30.0 adds the generation config's eos ids to each
  request's stop token ids, so the model's end of sequence comes back as `finish_reason` `stop`
  with the eos id as `stop_reason`; it reads `eos`. An id that is also one of the caller's
  `stop_token_ids` reads `stop-token`, and the source says it is also an eos id. Where no eos id can
  be read, a token-id `stop_reason` reads `stop-token`, and the source says the eos ids were not
  read.
- **The three stop forms are read only when `finish_reason` is `stop`.** A request that ends by
  repetition carries the string `stop_reason` `repetition_detected`, and reads `repetition`, never
  `stop-string`.
- **`stop-string` cannot be reached on an engine started with `skip_tokenizer_init`:** with no
  tokenizer, vLLM finds no stop string. It stays defined for an engine with a tokenizer.
- **A finished output with no finish reason:** `not observed`, source `the engine gave no finish
  reason`. vLLM 0.30.0's source, as read, gives one on every path a finished output takes.
- **A finish reason outside these:** `not observed`, source `finish_reason '<value>' is not one this
  adapter reads`.
- **Never the string `"None"`.** A hosted record's `output.finish` is unchanged: the provider's
  string, or `error (HTTP <status>)`. A self-hosted call with no capture is written as 1.0, with
  vLLM's `finish_reason` as it is.
- **A request with no output.** Under `LLM.generate`, a request aborted by the client comes back with
  no output at all. A call whose outputs are fewer than its requests is an error naming the requests
  that came back with none, and no record is written for any of the call's requests.
- **An output that is not finished.** A `RequestOutput` whose `finished` is false, as a wrapper
  around the engine may hand over before a request ends, is refused as a missing output is: no record
  is written for any of the call's requests, and the error says, for each, `request <i>: the engine's
  output is not finished, so no record was written for this call`, with its `fix:` line. "A finished
  output with no finish reason", above, is about a finished output only.

### The refusal at L3

L3 covers greedy decoding with nothing set that acts on the row. The adapter checks the engine and
every request of the call before it submits any, and when one is not covered it refuses the whole
call (`L3Refused`), naming each request and member in request order, each with its `fix:` line, and
nothing runs:

```
L3 refused for request 2: SamplingParams.presence_penalty is 0.5; with it set, the digested row is not the row the token was chosen from
fix: ask for L2 for this call, or leave presence_penalty at its default
```

| `SamplingParams` member | Covered when | Acts on the row |
|---|---|---|
| `temperature` | 0 | with any other value, the choice is not the argmax of the digested row |
| `repetition_penalty`, `presence_penalty`, `frequency_penalty` | 1, 0 and 0 | after the digest: the token is chosen from a row the digest did not cover |
| `logit_bias`, `allowed_token_ids`, `bad_words` | unset | before the digest: the digest covers a changed row, not the model's |
| `min_tokens` | 0 | before the digest, as `logit_bias` |
| `thinking_token_budget` | unset | after the digest, as the penalties |
| `structured_outputs` | unset | before the digest: vLLM applies the mask to the logits before it samples |

An L3 record carries each of these as `sampling.<name>`, `declared, not observed`, source
`SamplingParams.<name> as the caller built it, not read back from the engine`, at its value: `1.0`,
`0.0`, `0`, or `none` for an unset list or map. vLLM refuses structured outputs on an engine started
with `skip_tokenizer_init`; the adapter checks it all the same. Each request's record carries its own
request's members, whether the call is given one `SamplingParams` or one per request.

**The engine is checked too,** before any request:

| Engine setting | Refused when | The line |
|---|---|---|
| the V1 pin | the engine was not started by `capture.vllm.start(level="L3")` | `L3 refused: the engine was not started by capture.vllm.start(level="L3"), so the V1 model runner is not pinned` |
| HiSparse attention | `attention_config.hisparse_config` is set: it forces the V2 model runner over the pin | `L3 refused: the engine's attention_config.hisparse_config is set; …` |
| a watermark | `watermark_config` is set: it forces the V2 model runner over the pin | `L3 refused: the engine's watermark_config is set; …` |
| the runner read back | it reads V2 after the pin | `L3 refused: the engine's configuration reads the V2 model runner after the adapter's pin` |
| the engine core | its client is read as running it in another process: L3's digests stay there | `L3 refused: the engine core runs in another process (llm.llm_engine.engine_core is <class>), so L3's digests stay in that process`, with `fix: start the engine with capture.vllm.start(level="L3", ...) in the process environment, with nothing that sets VLLM_ENABLE_V1_MULTIPROCESSING to 1` |
| the worker | any `parallel_config` member below with another value, or none that can be read; any other parallel size above 1; the executor as built not read, or not the configured one: L3 is covered only where the engine's executor runs its worker in the calling process | one line per member, `L3 refused: the engine's parallel_config.<member> is <value>; …`, with `fix: ask for L2, or start the engine with <member> <value that runs here>`; for the executor as built, the lines below |
| a logits processor | any but L3's own that is not argmax-invariant, wherever it sits: one before L3's changes the row the digest covers, one after changes the row the token is chosen from | `L3 refused: engine logits processor <i>: <module>.<class>; before L3's digest …`, with `fix: ask for L2, or start the engine without it` |

- **The worker is checked where it is shown to run here,** not by listing the ways it does not. Each
  member that differs gets a line of its own, in this order, naming the member and its value:

  | `parallel_config` member | Runs here at | The line after the value |
  |---|---|---|
  | `tensor_parallel_size` | `1` | `tensor parallelism above 1 runs the workers in other processes, so L3's digests stay there` |
  | `pipeline_parallel_size` | `1` | `pipeline parallelism above 1 runs the workers in other processes, so L3's digests stay there` |
  | `prefill_context_parallel_size` | `1` | `prefill-context parallelism above 1 runs the workers in other processes, so L3's digests stay there` |
  | `data_parallel_size` | `1` | `L3 is covered only at data parallel size 1, where the one engine's worker runs in the calling process` |
  | `distributed_executor_backend` | `uni` | `L3 is covered only where the uni executor runs the worker in the calling process` |

  The first three make world size 1. A size that cannot be read is shown as `not read`, and an
  executor that cannot be read as `none`; both are refused. Any executor but `uni` is refused, a
  subclass of `uni`'s own class given as a class among them.
- **Every other parallel size above 1 is refused too,** `decode_context_parallel_size` and
  `data_parallel_size_local` among them: any `parallel_config` member whose name holds
  `parallel_size`, after the five above, by name, `L3 refused: the engine's parallel_config.<member> is
  <n>; L3 is covered only where every parallel size is at most 1`, with `fix: ask for L2, or start the
  engine with <member> 1`.
- **The executor as built is checked against the configuration.** Where it is not read: `L3 refused:
  the engine's executor as built is not read (llm.llm_engine.model_executor is not there), so its
  worker is not shown to run in the calling process`. Where it is not the configured one: `L3 refused:
  the engine's executor as built is <name> (llm.llm_engine.model_executor is <class>), where
  parallel_config.distributed_executor_backend reads <configured>`. Each with its `fix:` line.
- **The engine's logits processors** are the ones vLLM builds for it: the installed plugins of the
  entry-point group `vllm.logits_processors`, then the ones given to the engine, numbered from 0 in
  that order. Each is built in the calling process to ask `is_argmax_invariant()`; one that cannot be
  built there is refused.
- **An argmax-invariant processor** does not run under greedy decoding, so it is not refused. An L3
  record lists it in `engine.settings.logits_processors`, `observed`, source `the engine's logits
  processors as the adapter started it, besides L3's own`, at `none` when there is none.

### What a one-GPU, text-only engine does not reach

On a one-GPU, text-only vLLM 0.30.0 engine, four things this page describes are not reachable. Each
code path stays, with its test against the fake engine:
- **the `abort` ending:** vLLM gives an aborted request under `LLM.generate` no output, so the call
  is refused as "a request with no output", not recorded as `abort`;
- **the zero-token record:** vLLM refuses `max_tokens` below 1, and an abort before the first step
  gives no output;
- **the parallel-size refusal on a running engine:** vLLM refuses a world size above the node's GPUs
  first, so no engine starts for L3 to refuse;
- **the `error` ending:** its paths in vLLM need structured outputs, a KV connector, multimodal input,
  or the engine core in a process of its own.

### On a GPU of compute capability 12.x

On a GPU of compute capability 12.x (Blackwell), FlashInfer's compile step needs a CUDA toolchain of
12.9 or later, which a pip `nvidia-cuda-nvcc` provides. That is a requirement of the GPU and of
FlashInfer, not of onetrace: the adapter compiles nothing. The GPU check met it on such a GPU, and set
the toolchain up without changing vLLM.

### `sha256-tree-512/v0`

Over a byte string m:
- **H(m) = SHA-256(m)** when m is at most 512 bytes;
- **otherwise H(m) = H(SHA-256(c₀) ‖ … ‖ SHA-256(cₙ₋₁))**, where c₀ … cₙ₋₁ are m's consecutive
  512-byte chunks, the last one shorter when 512 does not divide m's length, and ‖ joins the 32-byte
  digests in chunk order.

The input is the logits row's float32 values as they sit in memory, little-endian, in vocabulary
order, with no copy, conversion or reordering. The empty input gives SHA-256 of the empty string; a
logits row is never empty, and the SDK refuses an empty row before it digests one. The output is the
final digest as **64 lowercase hexadecimal characters, with no prefix**: everywhere else in a record,
`sha256:<hex>` is the plain SHA-256 of the named bytes, and this digest is not.

```python
def tree512(m: bytes) -> str:
    while len(m) > 512:
        m = b"".join(hashlib.sha256(m[i:i + 512]).digest() for i in range(0, len(m), 512))
    return hashlib.sha256(m).hexdigest()
```

**The method's test vectors.** The byte strings have byte i = i mod 251. The row is 151,936 float32
values, value i = float32(r.random() × 64 − 32) for `r = random.Random(20261030)`, packed
little-endian. `tests/test_tree512.py` checks each, through the reference in `tests/tree512.py`.

| Input | `sha256-tree-512/v0` |
|---|---|
| 0 bytes | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 1 byte | `6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d` |
| 512 bytes | `d86e386278a71782a283f96aae4f4e7437471abef71136bd2811f98245488d89` |
| 513 bytes | `af03b0360647e12bfa680604a52fe9216fd9304c071daa000254ab0650a613b3` |
| 1,024 bytes | `d926a38a6e800e3795e8acbf9c0842d279faf72f61af254f17ae4aecaeb70187` |
| 1,025 bytes | `bb8b24b99a2a4b500a9380ef88e9bf210fd25a84c48d78e59d926a911532ab83` |
| the row (607,744 bytes) | `458ded0881470ec3e41a77bfd901aacf699ccc3a6fc0694e370dedd44e3bb9a8` |

At 512 bytes and below the method equals plain SHA-256. The 1-, 513- and 1,025-byte inputs test the
definition at a chunk edge; a float32 row never has those lengths.

## Comparing two records

`onetrace.model_call.compare(a, b)` reads two records and returns one of three results, and nothing
else:

- **`same`** — the compared fields are equal under the stated mode.
- **`diverged`** — naming the first field that differs.
- **`could not compare`** — naming each condition that was not met, in order.

A comparison names the mode it applied (1, 2 or 3) and what it rested on. It measures nothing. vLLM
with batch-invariant mode not observed on, at a submitted batch size over 1, **is not compared**: the
reason says that, and claims no property of such a configuration. The evidence for that condition is
one measurement, named in full, applied to every such record with no other configuration having been
measured.

When the two sides' per-step token-id sequences are given to `compare` and the result is `diverged`,
the first differing step is added as a **line of that diverged result** — never as a fourth result.
The three results stand.

Comparing two records is `onetrace.model_call.compare`: the verbs `onetrace diff` and `onetrace
localize` do not read records in 0.6.0 or 0.6.1.

## The verifier's rows

A verifier that reads a run gains rows **only for a run that holds a record**; a run with no record
gains no row, and its output is unchanged. For each record the run holds, the rows read exactly as the
receipt rows do — `PASS`, `FAIL` or `NOT-RUN`, never a guess, the matched text of a credential never
echoed:

- the record parses and its bytes are canonical;
- the record format is one the verifier implements (`model-call-record/1.0` and, from this release's
  onetrace-verify, `/1.1`); a format it does not implement reads `NOT-RUN`, naming it, and the run's
  exit is unchanged;
- the fields are complete and well formed;
- no field holds a value where it is `not observed` or `not applicable`;
- no credential material: an authorization-header shape in any string is a `FAIL`, by structure only —
  the verifier is never given the key.

A `model-call-record/1.1` record gains its own rows; a 1.0 record gains none:

- `steps members`: every `steps.*` member in its state and value set, as the 1.1 section above gives
  them; `k_returned_min` at most `k_returned_max`, at most `k_requested`, and, self-hosted,
  `k_requested` at most `sampling.logprobs`; `steps.logprobs` in a hosted record alone; `steps.surplus`
  exactly at L3. NOT-RUN `no capture taken` with no `steps.level`, and, for L3's missed-digest record,
  its reason;
- `steps names an output`: the `steps` digest is the digest of the step's own output
  `model_call.<n>.steps.json`, classed `model-generated`, read from the receipt; NOT-RUN where `steps`
  is not observed;
- `steps file`: the file lined up with the record, as the steps-file section above gives it (and the
  hosted form's steps, candidates and `logprob` rule). NOT-RUN `the steps file was not kept`, or `the
  steps file was not written` for the missed-digest record. The credential check covers its strings;
- self-hosted: `model runner`, `engine core` and `executor` (at L3 as `start` gives them: V1 pinned,
  the engine core in the calling process, `uni` as configured and as built), `L3 sampling` (each
  covered member at its value, and `engine.settings.logits_processors`), and `how it ended` (one of the
  seven endings, or `not observed`).

## The model link

`ot.model_from(provisioning_run, stages=[...], serve_stage=...)`, passed as `@ot.run(model=...)`,
links a run to the run that fetched, optionally quantised and served its model — the same shape as the
corpus link, one hop further. The link is the provisioning run's chain head, recorded on exactly the
named steps; the provisioning run is verified when the query run starts, and refused if it does not
verify, as a corpus link is. Following a model link one hop in a comparison, and cross-checking a
record's `model.files_digest` against the provisioning run's own digest, are later work and are not
done yet.

## What this does not claim

- **onetrace does not read the model's reasoning.** The record holds no hidden reasoning.
- **A record is not a correctness claim.** It does not check whether an answer is semantically
  correct.
- **A differing value is not a cause.** The record names no causality from a differing value alone.
- **A record does not reproduce across machines.** It claims no reproducibility across GPUs, versions
  or engines.
- **A record says nothing about a hosted provider's internals.** Those are `not observed`.
- **Record equivalence is not correctness**, and `same` covers only the compared fields.
- **The comparator's not-repeatable condition rests on one measurement** and fits no tolerance; it
  claims no cause.
- **A digest is not a commitment.** A digest in the record names a value; it does not bind the writer
  to anything, and is not a proof of what was served.
- **The companion result was measured at one arrangement.** That a filler request changed a target's
  answer was measured at batch 4 only, with the target first, companions no longer than the target,
  and no fillers beyond the companions; it is not a claim about other batch sizes or arrangements.
- **The tolerant form is not a detector of small numeric changes.** It is built to miss them; a small
  numeric change can leave the tolerant form unchanged.
- **The exact form is the full row for a transformers prefill, and the top 16 unrounded for a vLLM
  call.** It is not the full vLLM distribution.
- **The per-step capture holds the model's token ids.** It is `model-generated`, kept in a separate
  output, and the record names only its digest; a prefix-digest chain over token ids reveals the
  tokens to anyone with the vocabulary. The cost of L1 or L2 is not measured, and L3 is not measured.

## The schema

`docs/model_call_record.schema.json`, labelled `model-call-record/1.0`, is the schema of 1.0, and
`docs/model_call_record_1_1.schema.json`, labelled `model-call-record/1.1`, is the schema of 1.1. Each uses
only the validation keywords a strict reader applies, so the reader can read it; it declares the
optional `steps` capture member; `x-groups` groups the fields for a reader, with a group for the
capture member; and `x-most-bytes` bounds a record's size, with its reason (the record holds digests
and short value objects, and the per-step capture lives in a separate output, so the record does not
grow with capture depth).

The 1.1 schema adds the capture's own members (`steps.*`), `identity.digest` and the call kind
`endpoint`, and groups the capture's members together. It holds members and their value-object form;
the states and values the 1.1 section gives are the verifier's rows. `record.validate` and the schema
agree on both versions: a record the SDK writes passes both, and a member outside its version fails both.

The wheel carries a byte-identical copy of each as package data,
`onetrace/model_call/model_call_record.schema.json` and
`onetrace/model_call/model_call_record_1_1.schema.json`, readable with
`importlib.resources.files("onetrace.model_call").joinpath(<name>)`.
