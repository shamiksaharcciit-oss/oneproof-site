# LlamaIndex

`examples/llamaindex_adapter/pipeline.py` — the same nine stages as the
[plain-Python reference](plain-python.md), wired onto real LlamaIndex constructs:

| Stage | LlamaIndex construct |
|---|---|
| `document in` / `cleaned` | Plain Python — no construct exists in LlamaIndex (or LangChain, or Langflow) for either. |
| `converted` | LlamaIndex's own document readers. |
| `split` | LlamaIndex's own text splitting. |
| `embedded` | `MockEmbedding` — LlamaIndex's own no-credential, no-network embedding stub. |
| `indexed` / `retrieved` | `VectorStoreIndex` — pure in-memory Python, no external service, so this is genuinely native here (unlike Langflow's own knowledge-store component; see [the Langflow page](langflow.md)). |
| `answer` | A real `CustomLLM` subclass — LlamaIndex's own extension point for a model — invoked through `.complete()`, with deterministic regex extraction behind it: substituted logic behind a native integration point, not a native answering model. |

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

Needs the exact pins in `examples/llamaindex_adapter/requirements.txt` (conflicts with
LangChain's own `numpy` pin — see `examples/PIN_DISCIPLINE.md` for running more than one
adapter's requirements in the same environment).

<!-- quickstart: run -->
```
pip install -r examples/llamaindex_adapter/requirements.txt
python examples/llamaindex_adapter/pipeline.py OUT_DIR RUN_ID
```

`OUT_DIR` is a new folder for the run's record, for example `runs/first`: a folder that already holds a run is refused. `RUN_ID` is a name you choose for the run, for example `first`.

Its runs always store each chunk's text in their outputs (`chunks.json`, and again in `vectors.json`), along with the documents' converted and cleaned text, so treat its run folders like logs that may contain sensitive data.
