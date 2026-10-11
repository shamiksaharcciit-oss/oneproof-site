# Langflow

`examples/langflow_adapter/pipeline.py` — the same nine stages as the
[plain-Python reference](plain-python.md), wired onto Langflow's own runtime wherever it has one:

| Stage | Langflow construct |
|---|---|
| `document in` / `cleaned` | Plain Python — no construct exists in Langflow (or the other two frameworks) for either. |
| `converted` / `split` | Run inside Langflow's real graph execution engine (`lfx.graph` + `lfx.cli.common.execute_graph_with_capture` — the same machinery `lfx run` itself uses, in-process rather than shelled out), via flows built with `lfx.graph.flow_builder`, Langflow's own pure-Python flow constructor. |
| `indexed` / `retrieved` | **Substituted**, not native — Langflow's `KnowledgeComponent` requires Langflow's own API/database service layer to create a knowledge base, and no headless path (CLI or the real server's own build API) exposes that in the version this adapter pins. The substitution is named as one in the run, never presented as if it were native. |
| `answer` | A substituted, deterministic extraction step behind a Langflow extension point — no real model, no network. |

This is the one adapter of the three where a stage genuinely can't be run natively at all given
the tooling available, rather than merely lacking a first-class construct for it (`document in`
and `cleaned` are the "no construct exists" case in all three; `indexed`/`retrieved` here is
"a construct exists, but it needs infrastructure this adapter doesn't stand up"). Both are
substitutions, and both are named as such — the standing rule is: use the framework's own
runtime wherever it has one, substitute only where none exists at all, and never let a
substitution pass as native.

## Get this code

The example's files are not part of the installed `onetrace` package. They come in its source
package on PyPI, a `.tar.gz` file you download and unpack. In a terminal, in an empty folder, with
your virtual environment active, run:

<!-- quickstart: run -->
```
pip download onetrace==0.2.1 --no-binary :all: --no-deps
tar -xzf onetrace-0.2.1.tar.gz
cd onetrace-0.2.1
```

The first line downloads the source package without installing it, the second unpacks it into a
folder named `onetrace-0.2.1`, and the third moves into that folder. Run the commands below from
there. `tar` comes with current Windows, macOS and Linux; on Windows, use PowerShell.

## Running it

Needs the exact pins in `examples/langflow_adapter/requirements.txt` (see
`examples/PIN_DISCIPLINE.md` for running more than one adapter's requirements in the same
environment).

<!-- quickstart: run -->
```
pip install -r examples/langflow_adapter/requirements.txt
python examples/langflow_adapter/pipeline.py OUT_DIR RUN_ID
```

`OUT_DIR` is a new folder for the run's record, for example `runs/first`: a folder that already holds a run is refused. `RUN_ID` is a name you choose for the run, for example `first`.

Its embedder, Langflow's own test embedder, gives random numbers by design. So two runs of this
example differ from the `embedded` stage onward, and `onetrace diff` shows that stage as the first
difference. That is expected, and not a fault.

Its runs always store each chunk's text in their outputs (`chunks.json`, and again in `vectors.json`), along with the documents' converted and cleaned text, so treat its run folders like logs that may contain sensitive data.
