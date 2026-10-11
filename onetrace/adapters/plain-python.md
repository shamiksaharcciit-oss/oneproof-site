# Plain Python (no framework)

`examples/plain_python_control/pipeline.py` — the reference path every framework adapter is
compared against: the same nine stages (`document in`, `converted`, `cleaned`, `split`,
`embedded`, `indexed`, `retrieved`, `prompt built`, `answer`) over the same corpus, with no
RAG/agent framework anywhere in the file, not even an orchestration layer of onetrace's own.

Two third-party imports, both used directly rather than through a framework: `pypdf` (there's no
PDF parser in the standard library) and the standard library's own `html.parser` for HTML.
Everything else — cleaning, chunking, embedding, indexing, retrieval, prompting, answering — is
hand-written standard-library Python.

The embedder deliberately avoids numpy: it expands `sha256(text)` through `hashlib.shake_256`
into a fixed-length byte stream, so embedding similarity is deterministic and needs no floating
point at all. This is what makes this adapter, unlike the three framework ones, safe to run and
compare bit-for-bit on any machine — a real floating-point embedder's own output can legitimately
differ across numpy/BLAS builds even for identical code and inputs (this project's own test
suite measures how much, and under which configurations).

Instrumented via `onetrace.emit.Recorder` exactly as the framework adapters are — the point of
this pipeline is that a framework is never required to produce a valid stage-receipt chain.

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

It needs one package, `pypdf`, at the version its requirements file pins:

<!-- quickstart: run -->
```
pip install -r examples/plain_python_control/requirements.txt
python examples/plain_python_control/pipeline.py OUT_DIR RUN_ID
```

`OUT_DIR` is a new folder for the run's record, for example `runs/first`: a folder that already holds a run is refused. `RUN_ID` is a name you choose for the run, for example `first`.
