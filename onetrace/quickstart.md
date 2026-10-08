# Quickstart

Add onetrace to a small pipeline in two steps: one stage first, then the rest. Then switch it off, and take it out. Everything here runs offline, with no model and no key, in a few seconds.

Use a fresh virtual environment with Python 3.10 or later. Each command runs from the folder you save the files in.

<!-- quickstart: run -->
```
pip install onetrace
```

## Your pipeline

A pipeline in two modules: `steps.py` finds passages, `app.py` answers from them. Save both.

<!-- quickstart: file steps.py -->
```python
CORPUS = [
    "The warranty covers manufacturing defects for twelve months.",
    "Shipping delays are handled by the courier, not the warranty.",
    "Batteries have a separate six-month warranty.",
]


def retrieve(question: str) -> list[str]:
    words = set(question.lower().rstrip("?").split())
    return sorted(CORPUS, key=lambda p: -len(words & set(p.lower().rstrip(".").split())))[:2]
```

<!-- quickstart: file app.py -->
```python
from steps import retrieve


def answer(question: str, passages: list[str]) -> str:
    return passages[0]


def main(question: str) -> str:
    return answer(question, retrieve(question))


if __name__ == "__main__":
    print(main("How long does the warranty cover defects?"))
```

<!-- quickstart: run -->
```
python app.py
```

<!-- quickstart: output -->
```
The warranty covers manufacturing defects for twelve months.
```

## Step 1: one stage

Add one import and two decorators to `app.py`, and change nothing else: `@ot.run` on the function that does the whole job once, and `@ot.stage` on one step.

<!-- quickstart: file app.py -->
```python
import onetrace as ot
from steps import retrieve


@ot.stage("answer", instrument=ot.pkg("first-passage", "onetrace", kind="model-call"))
def answer(question: str, passages: list[str]) -> str:
    return passages[0]


@ot.run()
def main(question: str) -> str:
    return answer(question, retrieve(question))


if __name__ == "__main__":
    print(main("How long does the warranty cover defects?"))
```

`ot.pkg` names the tool a stage uses: a short id, the installed distribution whose version is recorded, and its `kind`. This demo isn't an installed project, so it names `onetrace`; in your own code, name the library that does the work, or your project's own distribution.

<!-- quickstart: run -->
```
python app.py
```

<!-- quickstart: output -->
```
The warranty covers manufacturing defects for twelve months.
```

The run wrote a folder under `runs/`, named by its run id. `onetrace doctor` checks the installation and verifies the most recent run:

<!-- quickstart: run -->
```
onetrace doctor
```

<!-- quickstart: output -->
```
...
7 checks; all passed
```

**What this one-stage run records.** Two receipts, not one:

- **`intake`**: `@ot.run` records the run function's arguments as a stage of their own. Here, the digest of `question`.
- **`answer`**: its arguments (`question` and `passages`), each as a SHA-256 digest of its encoding ([rule V1](manual.md#1616-numbers-and-booleans-rule-m-for-settings-rule-v1-for-values)), and its return value, stored as `return.json` in the run folder.

And what it doesn't:

- **`retrieve` is not recorded at all.** It isn't decorated, so the record has no step for it and no boundary in its place. Its result reaches `answer` only as an argument's digest. If the passages change, the record shows `answer`'s input changing, and nothing about why.
- **Nothing about meaning.** No stage says where its input came from (`trust`), where its output came from (`output_trust`), or whether it can be re-run to the same result (`rederivable`). onetrace records the most cautious value and lists each such field as `undeclared` on the stage. A person decides those; see [the manual's Decorators section](manual.md#16-decorators).

## Step 2: the other stage, in another module

Decorate `retrieve` in `steps.py`:

<!-- quickstart: file steps.py -->
```python
import onetrace as ot

CORPUS = [
    "The warranty covers manufacturing defects for twelve months.",
    "Shipping delays are handled by the courier, not the warranty.",
    "Batteries have a separate six-month warranty.",
]


@ot.stage("retrieve", instrument=ot.pkg("word-overlap", "onetrace", kind="retriever", config={"top_k": 2}))
def retrieve(question: str) -> list[str]:
    words = set(question.lower().rstrip("?").split())
    return sorted(CORPUS, key=lambda p: -len(words & set(p.lower().rstrip(".").split())))[:2]
```

A run records the stages defined in its own module ([`@ot.run`'s defaults](manual.md#1617-otruns-defaults) lists them all). `retrieve` is defined in another one, so list the run's stages, in order, on `@ot.run`. Without that list, the call to `retrieve` is refused, and the message names this fix. In `app.py`, change only the `@ot.run` line:

<!-- quickstart: file app.py -->
```python
import onetrace as ot
from steps import retrieve


@ot.stage("answer", instrument=ot.pkg("first-passage", "onetrace", kind="model-call"))
def answer(question: str, passages: list[str]) -> str:
    return passages[0]


@ot.run(stages=["retrieve", "answer"])
def main(question: str) -> str:
    return answer(question, retrieve(question))


if __name__ == "__main__":
    print(main("How long does the warranty cover defects?"))
```

<!-- quickstart: run -->
```
python app.py
```

<!-- quickstart: output -->
```
The warranty covers manufacturing defects for twelve months.
```

<!-- quickstart: run -->
```
onetrace doctor
```

<!-- quickstart: output -->
```
...
7 checks; all passed
```

Now `retrieve` has a receipt of its own. Its setting (`top_k`) is part of its instrument's recorded config, so a change to it shows as a changed config. `answer` records the passages as `retrieve`'s output: an edge from one stage to the next.

When a run closes, onetrace prints two lines to stderr: the folder it wrote, and the command that verifies it ([what a run says when it closes](manual.md#1618-what-a-run-says-when-it-closes-onetrace_quiet1)). `ONETRACE_QUIET=1` turns them off.

<!-- not executed: the run id differs on every run -->
```
onetrace: run written to runs/<run id>
next: onetrace-verify --require-artifacts runs/<run id>
```

That command verifies one run by name. In a terminal it looks like this. The first line is the verifier's summary, printed to stderr, so the rows on stdout stay exactly as the reference verifier prints them. When a row fails, it also prints to stderr, under the summary, a `fix (…)` line for each failing row: what to change, and the section of the errors page that explains it. `ONETRACE_QUIET=1` silences these stderr lines too, the summary and the fix lines alike:

<!-- not executed: the run id differs on every run -->
```
$ onetrace-verify --require-artifacts runs/<run id>
record intact: 3 stages, 2 output files checked
[PASS   ] receipts/01-intake.json: receipt format
...
80 pass, 0 fail, 4 not-run  ->  PASS
```

To compare two runs:

<!-- not executed: each run id stands for a folder under runs/ -->
```
onetrace diff runs/<first run id> runs/<second run id>
```

## Switch it off

`ONETRACE_DISABLE=1` makes both decorators pass straight through: the functions run as they did before, and nothing is written.

In a macOS or Linux shell:

<!-- quickstart: run os=posix -->
```
ONETRACE_DISABLE=1 python app.py
```

<!-- quickstart: output -->
```
The warranty covers manufacturing defects for twelve months.
```

In Windows PowerShell:

<!-- quickstart: run os=windows -->
```
$env:ONETRACE_DISABLE = "1"; python app.py; Remove-Item Env:ONETRACE_DISABLE
```

<!-- quickstart: output -->
```
The warranty covers manufacturing defects for twelve months.
```

## Take it out

Delete `import onetrace as ot` from both files, and the three decorator lines. What's left is the code under "Your pipeline", and it runs as it did before. Your run folders stay under `runs/` until you delete them.
