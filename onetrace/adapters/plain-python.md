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
