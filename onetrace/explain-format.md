# onetrace-explain: what it reads, sends, checks and writes

`onetrace-explain` (a separate package, `pip install onetrace-explain`) suggests where to look in a
comparison. **An explanation is a suggestion about a record, never a reading of it.** onetrace's
verdicts, exit codes and `onetrace summary` are what they are without it; the deterministic tools
never call a model and never read an explanation back. This page fixes the formats a reader of an
explanation (the console, a script) can rely on. Version 2, `0.2`: the two-run form below; the
report-folder form and its packet, `0.1`, are unchanged.

## The command

```
onetrace-explain REPORT_DIR [--model PROVIDER:NAME] [--dry-run] [--include-text] [--redact NAME]... [--yes] [--out DIR]
```

`REPORT_DIR` is a folder `onetrace diff` or `onetrace localize` wrote with `--out`. Exit codes are its
own and say nothing about the runs: 0 an explanation or a dry run was written; 2 a usage error, or a
comparison that can't be explained (no report, a refused or could-not-check verdict, a run whose
chain head is not the one the report checked); 3 the model couldn't be reached, or replied with no
usable JSON. Never use it as a CI gate.

## The model and its key (0.3)

The model is named in the `[model]` table of `~/.config/onetrace/explain.toml` (or the file
`ONETRACE_EXPLAIN_CONFIG` names), or with `--model`. The key is never in that file. It is read at
send time, from one of two places, as `key_source` says:

| `key_source` | Where the key is read |
|---|---|
| `"env"` (the default) | the environment variable `key_env` names. A local server that takes no key needs no `key_env`. |
| `"keyring"` (0.3) | the operating system's keychain (Windows Credential Manager, the macOS Keychain, the Secret Service on a Linux desktop), through the `keyring` package: `pip install "onetrace-explain[keyring]"`. Service `onetrace-explain`, user `<provider>:<base_url>`, or `<provider>:default` where the file names no `base_url`. |

```toml
[model]
provider = "anthropic"
name = "<model name>"
key_source = "keyring"     # or leave it out and name key_env = "ANTHROPIC_API_KEY"
```

The key is read before anything is sent. Where it can't be read, or holds a line end, another
control character or a character outside ASCII (a variable set from a file with CRLF line ends, a
zero-width space or a curly quote from a paste), nothing is sent
and the model is not asked: `onetrace-explain REPORT_DIR` exits 2, and `onetrace-explain RUN_A RUN_B`
records "not asked" with the reason, its exit code still `onetrace diff`'s. The message says where it
looked and what to do, never the key: the variable and the file that names it; or the keychain entry,
with the command that stores it (`python -m keyring set onetrace-explain <provider>:<base_url>`); or,
where the keychain can't be read, to unlock it or use `key_env`; or the install line where the
`keyring` extra is missing. An error met while a request carries the key is said by its type: an HTTP
error by its status code alone, never the server's reason phrase; another network error by its reason
(refused, timed out). Text holding the key, or any run of 8 of its characters, is never kept: an
error's text is said by its type alone, and a model's reply holding it is not kept, its length and
sha256 said in its place, with no explanation from it. Anyone who can run code as this user can read the
key from the keychain, as from an environment variable.

## Two runs: `onetrace-explain RUN_A RUN_B` (0.2)

```
onetrace-explain RUN_A RUN_B [--no-model] [--json] [--probes NAME,...] [--max-probes N] [--runs-root DIR]
                 [--mask FILE] [--model PROVIDER:NAME] [--yes] [--include-text] [--redact NAME]... [--out DIR]
```

It compares the two runs itself (`onetrace diff`, in this process) and prints four parts, in order.
Its exit code is `onetrace diff`'s for the two runs, whatever the model says, or whether one is
asked. It is `onetrace-explain RUN_A RUN_B`, not `onetrace explain`: onetrace's CLI takes no verb it
doesn't define, and onetrace is not changed. With one folder, `onetrace-explain REPORT_DIR`, it is
the 0.1 command below, unchanged.

1. **What changed (checked from the records).** The headline and the stage strip, from `onetrace
   diff`'s JSON report, in the console's words: Same, First difference, Changed after it, Same
   again, Couldn't check. Printed always, with no model and no network call.
2. **Evidence (read-only, no re-runs).** Probes: questions answered from records already written.
   A probe never re-runs a pipeline, calls a tool, changes a file or a setting, or reaches a host.
   Each one that ran states its sample: how many runs it read, and which. A probe whose needs are
   missing reads `not run: <what is missing>`, never skipped silently.
3. **What may have happened (AI-generated, may be wrong).** The model's claims. Each must cite a
   probe that ran (`probe/P1`, ...) or an item of the record, and the post-check below drops the
   rest and counts them. A claim citing a probe that did not run is dropped. Asked only when a
   model is configured and the kinds sent are consented to.
4. **Checks a human could run (not run).** Never run here. Each is marked "runnable here" or
   "needs a runner you name". A check that re-runs a step names that step's replay-safety label,
   `effect_label` (format 0.4), its `value` and its `basis`. A step labelled `write` or `unknown` is
   named as one whose re-run may change state outside the record, and `unknown` is read as `write`.
   A receipt with no label reads `effect not recorded`, never `unknown`: every record written
   before format 0.4 reads so.

### The probes

| Probe | Question | Needs | 0.2 |
|---|---|---|---|
| `variation` | Is the difference inside the range the baseline's repeat set shows at the step? | a repeat set under `--runs-root` (`repeat_of`, onetrace 0.6) | runs |
| `mask` | Does the difference vanish under the mask `onetrace mask suggest` proposes? | the two runs | runs |
| `model_call` | At a model step: what does the model-call comparator read? | a model-call record in both runs, its file kept | runs |
| `same_config`, `same_model_files`, `neighbours` | across a console's stored runs | a console store | `not run: no console store given`; `--store` is refused |
| `config_vs_reference`, `bisect`, `kind_of_change`, `close_call` | | console 0.6.0 | `not run`, naming it |
| `expectations`, `fallback` | | onetrace 0.7 | `not run`, naming it |

**The playbook** picks the probes from the first difference's kind, with no model, `mask` first:

- configuration changed (an instrument or a constant at the first difference): `mask`,
  `config_vs_reference`, `same_config`, `bisect`;
- same inputs, different model output (a model-call record at the first difference): `mask`,
  `variation`, `close_call`, `model_call`, `same_model_files`;
- inputs changed (the runs were given different recorded inputs): `mask`, `neighbours`;
- otherwise (the output differs only): `mask`, `variation`.

`--probes a,b` runs exactly those instead. At most `--max-probes` probes run (default 8); past the
bound, a probe reads `not run: past the bound of N probes`.

**A model may propose more,** once, from the same list only, beside its claims:
`{"probes": [{"probe": "<name>", "step": "<a node in the packet>", "run": "<a run id in the
packet>"}]}`. A proposal naming anything else (a command, a path, a host, a URL, another argument,
a step or run the evidence doesn't hold, a probe off the list) is refused and counted. So is one
past the bound, or one made after the first round. When a proposal runs, the model is asked once
more with the probe's result, and its second reply's claims are the ones checked.

### What is sent: `onetrace-explain-evidence/0.2`

The 0.1 packet below, built from the comparison's report, with each probe that ran as an item of
kind `probe` (`probe/P1`: the probe, its arguments, its one-line result, its result and its sample).
`not_run` lists the probes that did not run, with why, and they may not be cited. A probe's result
names runs by run id, never by a path of this machine. With `--no-model`, nothing is sent.

### What it writes

Under `OUT` (default `./onetrace-explain`): `compare/`, `onetrace diff`'s report; `probes/`, the
probes' own working files (a suggested mask, its masked comparison); and `explain/<run id>/`, the
explanation as a run of its own, with these stages:

- **`evidence`**: the report, and both runs' manifests and receipts in, by digest; what changed out;
- **`probe#P1`, `probe#P2`, ...**: one node per probe, its name, arguments, status and result
  digest as constants, and its result out;
- **`model#1`** (and **`model#2`** after a round of proposals): what was sent out, `sent.json`, then
  the raw reply, `reply.txt`, `model-generated`;
- **`post_check`**: what was kept and dropped.

Beside the run are `explain/<run id>.explanation.json`, the four parts as `--json` prints them, and
`explain/<run id>.explanation.txt`, as the command printed it.

### A worked pair

**Fixture data**, written by `tests/explain_fixtures.py` (`worked_pair`), with no model and no
network. A baseline with two repeats, and a candidate whose model step answered differently. The
model is a fake one, which replies with a fixed file, `reply.json`. Its third claim uses a causal
word, and the post-check drops it. `tests/test_explain_02.py` runs this and compares it with the output below,
line by line, the record's run id apart:

<!-- explain: worked pair, fixture data -->
```
$ onetrace-explain runs/base runs/cand --model fake:reply.json --out out
What changed (checked from the records)
  First difference at answer
    load                     Same
    answer                   First difference

Evidence (read-only, no re-runs)
  P1 mask  nothing to mask: the differences are not ids, times or folders onetrace masks   [2 runs: base, cand]
  P2 variation  at answer: 1 of 3 runs in the repeat set of base differ from its common output; the candidate's output is among the outputs the set recorded (2 distinct)   [3 runs: base, rep1, rep2]
  P3 not run: close_call (not in explain 0.2: it waits for console 0.6.0's near-tie reading (L2))
  P4 model_call  at answer: the model-call comparator reads could not compare: batch context not observed: batch.size, batch.padded_width, batch.position, batch.members, batch.fillers, batch.batch_invariant   [2 runs: base, cand]
  P5 not run: same_model_files (no console store given)

What may have happened (AI-generated, may be wrong)
  model: fake:reply.json
  - note: The repeat set already varies at answer: `1` of `3` runs differ from its common output, and the candidate's output is among the outputs it recorded.
    shown by: probe/P2
  - where to look first: The answer step's output differs with its inputs the same; the model-call record is the place to look.
    shown by: node/answer, probe/P4
  dropped: 1 says what caused a difference

Checks a human could run (not run)
  onetrace diff runs/base runs/cand --text --stage answer
      runnable here
  onetrace localize runs/base runs/cand --for answer
      runnable here
  onetrace reproduce runs/cand answer --runner <your runner>
      needs a runner you name; effect not recorded
recorded: out/explain/<run id>
```

The exit code is 1, `onetrace diff`'s for a pair that diverged. `--no-model` prints the first, second
and fourth parts, and sends nothing. `--json` prints the same four parts as one JSON object, in four
keys: `what_changed`, `evidence`, `what_may_have_happened`, `checks`.

## The evidence packet, `onetrace-explain-evidence/0.1`

One JSON object, its bytes sorted-key, no spaces, UTF-8, built the same from the same report:

```json
{"format": "onetrace-explain-evidence/0.1",
 "report": {"name": "localize.json", "sha256": "sha256:…"},
 "runs": {"baseline": {"run_id": "…", "chain_head": "sha256:…", "format": "stage-receipt-chain/0.3"},
          "candidate": {…}},
 "items": [{"id": "node/load/constant/chunk_size", "kind": "constant", "name": "chunk_size",
            "baseline": "512", "candidate": "1024"}, …],
 "kinds": ["constant", "for", "input", …]}
```

Each item has an `id` (what a claim cites) and a `kind`:

| kind | id | holds |
|---|---|---|
| `verdict` | `comparison/verdict` | verb, envelope, exit, first difference |
| `for` | `comparison/for` | the `--for` node, its result, origins, not reaching, the path's verdicts |
| `end_outputs` | `comparison/end_outputs` | the report's end outputs |
| `inputs_differ` | `comparison/inputs_differ` | the inputs that differ, and `on_different_inputs` |
| `mask` | `comparison/mask` | the mask's sha256, how many settings it masked |
| `node` | `node/<node>` | the node's verdict and annotations |
| `instrument` | `node/<node>/instrument` | id, kind, version, config digest, in each run |
| `outcome` | `node/<node>/outcome` | the outcome class in each run |
| `upstream` | `node/<node>/upstream` | the nodes it read |
| `constant` | `node/<node>/constant/<name>` | a constant that differs, both values (`redacted: true` and both digests with `--redact`) |
| `input`, `output` | `node/<node>/input/<name>` | digest and bytes in each run, `differs` |
| `text` | `node/<node>/output/<name>/text` | with `--include-text` only: both runs' kept text of an output that differs, at most 8192 bytes each |

In it as recorded: a constant's value, whatever it holds (a path, a token), and the report's
annotations, which may name an input's folders. `--redact NAME` sends a constant's name and digests
only. Never in it: anything not in the two runs or the report, a path of this machine's own folders
(the runs', the report's, the configuration's), an environment variable, the model key, a signing
key, an anchor's proof. `--dry-run` prints the packet's bytes, their size and
sha256, and sends nothing. The first send of a kind never sent to an endpoint before names the
kinds and asks; `--yes` skips the question for scripts, the list is still printed.

## The reply, and the post-check

The model is asked for one JSON object:

```json
{"claims": [{"text": "…", "kind": "lead" | "ruled out" | "note", "cites": ["<item id>", …]}],
 "checks": [{"check": "text" | "for" | "mask" | "reproduce" | "match", "node": "…", "setting": "…",
             "run": "baseline" | "candidate"}]}
```

The post-check is mechanical, with no model. Its lists of quoting forms, look-alike letters and causal words are lists: a reply can word around them, and a kept claim is a suggestion, never a reading. A claim is dropped when its kind is not one of the
three, it cites nothing, a cite is not an item of the packet, a value it quotes (in one of the quoting forms the post-check lists) is not a value of an item it cites, or it says what caused a difference ("cause",
"because", "due to", "led to", "resulted in", "the reason", "responsible for" and their like; a list
of words, which a model can still word around: a kept claim is a suggestion, never a reading). A check is dropped when it is not on the menu, names a node or
setting the packet doesn't hold, or a run other than `baseline` or `candidate`. Drops are counted,
by reason. When every claim is dropped the explanation reads "No suggestion could be tied to the
record" and shows the checks only. A lead is confirmed or ruled out only by what a check's own
command reports, never by the model.

## What it writes

Under `OUT/explain/` (`OUT` defaults to `REPORT_DIR`), for each explanation:

- `<run id>/`: a onetrace run of its own, format 0.3, three stages: `evidence` (the report and both
  runs' manifests and receipts in, by digest; `packet.json` out), `model` (instrument: the provider
  and model name, settings: the request parameters; `reply.txt` out, the raw reply byte for byte,
  `model-generated`), `post_check` (`checked.json` out). `onetrace-verify` checks it like any run.
- `<run id>.explanation.json`: `{"label", "model", "record", "claims", "checks", "dropped",
  "checks_dropped"}`, counts as decimal strings. This is what a reader shows.
- `<run id>.explanation.txt`: the same, as the command printed it.

Every explanation is shown under the label **"Suggested explanation — AI-generated, may be wrong"**,
with its model, apart from the verdicts. Two explanations of one comparison can differ; each keeps
its own record.
