# LangChain

`examples/langchain_adapter/pipeline.py` — the same nine stages as the
[plain-Python reference](plain-python.md), wired onto real LangChain constructs wherever one
exists for the job:

| Stage | LangChain construct |
|---|---|
| `document in` | Plain Python file enumeration — LangChain's own document loaders already return parsed text, so there's no LangChain construct that reads "raw bytes, not yet parsed." |
| `converted` | `langchain_community.document_loaders`: `TextLoader` (`.txt`/`.md`), `BSHTMLLoader` (`.html`), `PyPDFLoader` (`.pdf`). |
| `cleaned` | Plain Python NFKC/whitespace normalization — LangChain has no first-class cleaning primitive between loading and splitting. |
| `split` | `langchain_text_splitters.RecursiveCharacterTextSplitter`. |
| `embedded` | `langchain_community.embeddings.DeterministicFakeEmbedding` — no network, no real model, deterministic. |
| `indexed` / `retrieved` | LangChain's own in-memory vector store and retriever interface. |
| `answer` | A substituted, deterministic extraction step behind LangChain's own LLM extension point — no real model, no network. |

Where no LangChain construct exists at all (`document in`, `cleaned`), plain Python is used
instead and named as a substitution in the run, never silently folded into "this is what
LangChain does."

## Running it

Needs the exact pins in `examples/langchain_adapter/requirements.txt` (LangChain and LlamaIndex
pin conflicting `numpy` versions — install one adapter's requirements at a time, or use a
dedicated virtual environment per adapter; see `examples/PIN_DISCIPLINE.md`).

```
pip install -r examples/langchain_adapter/requirements.txt
python examples/langchain_adapter/pipeline.py OUT_DIR RUN_ID
```

## Keeping chunk text: `keep_text`

```
python examples/langchain_adapter/pipeline.py OUT_DIR RUN_ID --keep-text
```

or `main(out_dir, run_id, keep_text=True)` from Python. It is off by default.

- **Off (the default):** the `split` stage's chunk index (`chunks.manifest.json`) holds each chunk's id, document, length and digest, and **no chunk text**.
- **On:** each entry also holds `text`, the exact chunk string its digest is taken over, and the `split` stage records the constant `keep_text: true`. `onetrace diff --text` then shows a changed chunk's text, but only after checking that the digest of the text's bytes equals the chunk's recorded digest. Otherwise it says `text does not match its digest; not shown`.

What a run folder stores either way: each stage's outputs, which include documents' converted and cleaned text, prompts and answers. Inputs are only fingerprinted. Treat run folders like logs that may contain sensitive data. `keep_text` adds the chunk text to that.
