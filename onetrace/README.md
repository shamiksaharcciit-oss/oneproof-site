# Documentation

- [The record format, in plain words](format.md)
- [The five verdicts](verdicts.md)
- [The three verbs](verbs.md) — `diff`, `localize`, `reproduce`
- [What onetrace does not claim](non-claims.md)

## Adapters

Four pipelines, the same nine stages, the same corpus, instrumented the same way — one with no
framework at all, three wired onto a real RAG/agent framework's own runtime wherever it has one:

- [Plain Python (no framework)](adapters/plain-python.md) — the reference path the other three are compared against.
- [LangChain](adapters/langchain.md)
- [LlamaIndex](adapters/llamaindex.md)
- [Langflow](adapters/langflow.md)

See the [quickstart](quickstart.md) to run a pipeline and check
it yourself before reading further.
