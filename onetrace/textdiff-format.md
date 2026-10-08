# The `onetrace-textdiff/0.3` format

`onetrace diff A B --text --json` prints one JSON document describing the text that changed
between two verified runs. The same document is written under `text` in the JSON report in
`--out` for every `--text` run. The plain text `--text` prints is drawn from the same structure,
so the two forms always agree.

The document is **canonical JSON**, the SDK's own form: keys sorted, no insignificant whitespace,
UTF-8. Canonical JSON carries no numbers, so **every count, index, position, line number and offset is a decimal
string**, and `exit` is too.

## Top level

| Field | Meaning |
|---|---|
| `format` | `"onetrace-textdiff/0.3"` |
| `text_form` | `"escaped"`: every `text` field is displayed text, escaped as below. It is never raw record text. |
| `envelope` | `diff`'s own result: `identical`, `diverged`, `not comparable`, `refused` or `could not check` |
| `exit` | `diff`'s exit code, as a string. `--text` never changes it. |
| `shown` | `false` when no text is shown: a run didn't verify, or the runs can't be compared. `reason` then says which, and there are no nodes. |
| `first_line` | the sentence the plain form prints first, e.g. `first difference: retrieve — output text changed; settings unchanged; corpus link changed; input help_centre changed`: the clauses that apply, in that order |
| `unknown_stages` | `--stage` names that matched no node |
| `nodes` | the nodes shown, in the ladder's order |
| `corpus_traces` | present when a first-difference node's corpus link changed: the one-hop trace into the linked ingest runs, below. Absent otherwise. A first difference with no corpus link gets a line in the plain form only (`trace: no corpus link recorded at <node>; …`), and nothing here. |

## A node

| Field | Meaning |
|---|---|
| `node`, `verdict` | the node id and its ladder verdict (`FIRST DIFFERENCE`, `downstream`, `reconverged`, `same`, or `COULD NOT CHECK` for a node `--stage` names) |
| `settings` | the settings lines, e.g. `settings: none changed` or `settings: 1 changed` then `  constants.temperature: 0.2 -> 0.7`. The corpus link is not counted as a setting: when it changed, `corpus link changed: <digest> -> <digest>` follows as a line of its own (with each run id once a trace reached it). A reconverged node carries its settings lines only if a setting or the link changed. |
| `inputs` | one line per input whose digest or trust class changed, or that is on one side only, ending `content not stored` |
| `causes` | **on every `FIRST DIFFERENCE` node only:** every candidate cause compared, each `{kind, name, baseline, candidate, status}` with `status` `same` or `changed`. Kinds are `input` (value `{digest, trust_class}`), `tool` (`instrument.id`, `instrument.kind`, `instrument.version`), `setting` (`instrument.config_digest`, `instrument.manifest_digest`, `constants.<name>`) and `corpus link` (`assertions.corpus_manifest`, by digest). The console's cause table is drawn from this list and nothing else. |
| `presence` | when the node exists in one run only |
| `outputs` | the outputs whose digests differ |

## An output

| Field | Meaning |
|---|---|
| `name`, `media_type` | as the receipt records them |
| `verified` | `true` when the bytes were read and their digest equals the receipt's. Otherwise `false`, with `reason` (`not shown: <name> does not match its receipt`, or `… is missing`), and no hunks. |
| `kind` | `text` (a line diff: text, or JSON in canonical form), `chunk index`, `hits`, `binary`, `not diffed` (over the size or line cap), or `not shown` |
| `presence` | `only in the baseline` / `only in the candidate`, when the output exists on one side only |
| `notes` | lines that go with the output. With hunks: what the lines hide (`final newline removed`, `line endings CRLF -> LF`). Without: why there are none (`binary: …`, `too large to diff (…)`, `whitespace-only change: …`), or, for `chunk index` and `hits`, the rendered lines themselves. |
| `entries` | for `chunk index` and `hits`: one per chunk or hit that a `notes` line names, as the record holds it, **not escaped** (unlike `notes`, which are display lines): `id`, or, for a chunk with no id of its own, `doc` and its 1-based `position`; `change` (`changed`, `added`, `removed`, `entered`, `left`, `moved`); and `note`, the index of its line in `notes`. A cut output (`truncated`) keeps the entries of the lines it keeps, renumbered. New in 0.3. |
| `hunks` | the line diff, below |
| `truncated` | present when `--max-lines` cut the output: `{"more_lines": "<n>"}`, the same number the plain form prints in `… n more lines`. The JSON keeps exactly the lines the plain form still shows. |

## A hunk and its lines

A hunk is `{baseline: {start, lines}, candidate: {start, lines}, lines: [...]}`, with an optional
`note` (`no line could anchor this block …`). Each line is:

| Field | Meaning |
|---|---|
| `op` | `" "` unchanged, `"-"` removed, `"+"` added. (The plain form's `~` line, the changed words marked, isn't here: its content is the `spans`.) |
| `baseline`, `candidate` | the line's 1-based number on each side, or `null` on the side it isn't on |
| `text` | the line as displayed, escaped, and windowed if long |
| `spans` | `[start, end)` character offsets into `text`: on a `-` line the removed words, on a `+` line the added ones |

**Line numbers:**
- For text, they count the output's lines, split at LF.
- For JSON, they count the lines of its **canonical pretty form**, the text that is diffed: keys sorted, two-space indent, one member per line, numbers exactly as written.

**Spans:**
- A changed line pair is compared word by word, where a word is a run of letters and digits, of whitespace, or a single other character. The spans cover the changed words.
- A pair too long to compare word by word (over 20,000 characters, or over 2,000 words) gets one span on each side instead: the characters between the lines' common start and common end.

**Long lines:** a line over 2,000 characters is shown as a window of 2,000 characters, starting 40 characters before its first difference. It's written `… N characters … <window> … M more characters`, and spans count those markers.

## Escaping (`"text_form": "escaped"`)

Text is escaped one-to-one, the same way wherever the SDK shows record text:

1. **A backslash is doubled:** `\` becomes `\\`. This applies to text outputs. A JSON output's canonical form already writes its own backslashes as escapes, so there they are shown as written.
2. **Every control character and line break becomes `\uXXXX`,** in lowercase hex. That means the Unicode categories Cc, Cf, Zl and Zp, fixed as of Unicode 15.0 so output never varies with the Python that runs it. Beyond U+FFFF the character is written as a surrogate pair (`󠀁`). The code points are:

   `0000–001F 007F–009F 00AD 0600–0605 061C 06DD 070F 0890–0891 08E2 180E 200B–200F 2028–202E 2060–2064 2066–206F FEFF FFF9–FFFB 110BD 110CD 13430–1343F 1BCA0–1BCA3 1D173–1D17A E0001 E0020–E007F`

   So TAB is `\u0009`, CR `\u000d`, ESC `\u001b`, and a right-to-left override `‮`.
3. **An undecodable byte is `\xNN`** (text outputs only). No `\uXXXX` can be mistaken for it.
4. **A lone surrogate** that a JSON output's own `\ud800` escape decodes to is `\uXXXX`.

**A renderer displays `text` as given, HTML-escaped if it is HTML, and never escapes it again.** Escaping it again would double every backslash, and `spans` index into `text` exactly as delivered.

## A corpus trace

When a first-difference node's corpus link changed, the two linked ingest runs are found by chain
head (one level down in `--runs-root`, default the folder holding the baseline), verified, and
compared. `corpus_traces` is a list with one entry per distinct pair of chain heads, in the
ladder's order. Each entry:

| Field | Meaning |
|---|---|
| `node` | the first-difference node the trace starts from |
| `also_at` | the other first-difference nodes with the same pair, which get no entry of their own |
| `status` | `traced`, `could not check`, or `not followed` (`--no-follow`) |
| `baseline`, `candidate` | each `{chain_head, run_id, path, verified}`. `path` is relative to `--runs-root`, written with `/`. A side that wasn't found has `run_id`, `path` and `verified` `null`. One that doesn't verify has `run_id` `null` and `verified` `false`. A side with no link has `chain_head` `null` too. With `not followed`, only `chain_head`. |
| `reason` | with `could not check`: `linked ingest run not found: <digest>; pass --runs-root`, `linked ingest run did not verify: <path>`, `the baseline records no corpus link at <node>` (or `the candidate`), `the linked ingest runs are not comparable: <why>`, or `the linked ingest runs could not be compared: <why>` |
| `heading` | `traced into the linked ingest runs: <run id> -> <run id>` |
| `first_line` | e.g. `started at: load — 1 of 214 documents changed (help-centre/warranty.md); settings unchanged` |
| `documents` | `{changed, total, names}`, counted from the chunk indexes by digest, or `null` when the runs have none |
| `second_hop` | the ingest runs' own changed corpus link, `{node, baseline, candidate}`, named and never followed; otherwise `null` |
| `envelope` | the ingest comparison's result, `identical` or `diverged`. A pair that isn't comparable, or whose comparison couldn't be made, is not traced: its entry is `could not check`, with the reason. |
| `nodes` | the ingest comparison's nodes, shaped as above |

Nothing from an ingest run that doesn't verify appears, its run id and document names included.

## What stays the same

`--text`, `--json` and the corpus trace never change a verdict or an exit code. The inputs' content is never shown,
because inputs are fingerprinted, not stored. Stored chunk or hit text is shown only when the
digest of its bytes equals the recorded digest.
