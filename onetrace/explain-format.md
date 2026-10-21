# onetrace-explain: what it reads, sends, checks and writes

`onetrace-explain` (a separate package, `pip install onetrace-explain`) suggests where to look in a
comparison. **An explanation is a suggestion about a record, never a reading of it.** onetrace's
verdicts, exit codes and `onetrace summary` are what they are without it; the deterministic tools
never call a model and never read an explanation back. This page fixes the formats a reader of an
explanation (the console, a script) can rely on. Version 1, `0.1`.

## The command

```
onetrace-explain REPORT_DIR [--model PROVIDER:NAME] [--dry-run] [--include-text] [--redact NAME]... [--yes] [--out DIR]
```

`REPORT_DIR` is a folder `onetrace diff` or `onetrace localize` wrote with `--out`. Exit codes are its
own and say nothing about the runs: 0 an explanation or a dry run was written; 2 a usage error, or a
comparison that can't be explained (no report, a refused or could-not-check verdict, a run whose
chain head is not the one the report checked); 3 the model couldn't be reached, or replied with no
usable JSON. Never use it as a CI gate.

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
