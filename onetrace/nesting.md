# Nesting

A record shows which step called which, for stages and for whole runs, so that an agent that calls
a sub-agent (or a LangGraph subgraph) is one record a reviewer can walk down. A run with no nesting
writes receipts byte-identical to 0.4.0.

## Stage inside stage

A stage called while another is running records `parent` (the caller's node id) in its receipt, and
the caller's receipt lists its `children` in call order. A child's return given to another stage as
an argument is linked the usual way, as that stage's input, by digest. A child's return the caller
uses in its own body is not recorded as an input of the caller: the caller's receipt names the
child in `children`, and nothing more. One context variable holds the step running now; the span
context and nesting both read it.

## Run inside run

A decorated run started inside another's stage keeps its own folder and chain. Its manifest records
`parent_run` (the outer run's id) and `parent_stage` (the calling stage). The outer run records the
inner run as an input of the calling stage — named `run:<inner run id>`, with the inner run's chain
head as its digest — so the outer run is no longer empty.

A LangGraph subgraph node is an ordinary decorated stage, so it records as a nested step when it
runs inside another; its state-key edges stay as they are.

## The depth limit

Nesting is recorded up to a fixed depth (`onetrace.emit.NEST_DEPTH_LIMIT`, **32**; 1 at the top
level). A call nested deeper than the limit is refused and named, never left out, so a runaway
recursion cannot fill a record folder.

## Comparing nested runs

`onetrace diff` and `onetrace localize` name the first difference in chain order. A step's receipt
is written when the step ends, so a stage called inside another stage comes before its caller in the
chain. What the comparison prints depends on the shape:

- **A run started inside a stage.** The calling stage records the inner run as its input
  `run:<inner run id>`, so the calling stage is the first difference. Given both inner runs' folders
  (`--nested-run PATH`, once for each), the comparison descends into the inner run and names its first
  differing step: `inside <step>, into run <id> at <child>`. Without them it says `nested run <id>:
  folder not given`.
- **A stage called inside another stage.** Each stage is compared in its own right. When the child's
  output differs, the comparison reports two first differences, the child first in chain order and
  then its caller, and prints no `inside` line. A child called in one run only is reported as present
  in that run only, and its caller, whose output is the same, as `same`.

The `inside <step>, at <child>` line is printed only when the first difference is a step whose
recorded children differ from the other run's. Neither stage-inside-stage shape above prints it.

### A stage inside a stage, compared

`plan` calls `price_lookup` inside its own stage. Record it twice, with two prices:

<!-- the stage-in-stage example -->
```python
# order.py -- record it twice: python order.py 10, then python order.py 12
import sys

import onetrace as ot
from onetrace.emit import Instrument

PRICE = int(sys.argv[1])
TOOL = Instrument("order", "tool", "1.0.0", {})


@ot.stage("price_lookup", instrument=TOOL)
def price_lookup(item):
    return {"item": item, "price": PRICE}


@ot.stage("plan", instrument=TOOL)
def plan(item):
    p = price_lookup(item)            # a stage called inside plan's stage
    return {"item": item, "total": p["price"] * 2}


@ot.run(stages=["plan", "price_lookup"])
def main(item):
    return plan(item)


main("widget")
```

```
ONETRACE_RUN_ID=order-a python order.py 10
ONETRACE_RUN_ID=order-b python order.py 12
onetrace localize runs/order-a runs/order-b
```

The comparison, as `localize` prints it (exit 1, diverged):

<!-- localize output -->
```text
localize: diverged

node            A     B     verdict
--------------------------------------------------------------------
intake          1     1     same
price_lookup    2     2     FIRST DIFFERENCE
                            output return.json differs
plan            3     3     FIRST DIFFERENCE
                            output return.json differs

first difference  price_lookup, plan   (2 branches)
comparisons performed 3 of 3 nodes; same 1, FIRST DIFFERENCE 2, downstream 0, reconverged 0, COULD NOT CHECK 0
```

`onetrace diff runs/order-a runs/order-b` prints the same table and the same `first difference`
line under `diff: diverged`, and also exits 1.

## Verifying nested runs

onetrace-verify adds one row, **"nested runs match their recorded heads"**: give each inner run's
folder with `--nested-run PATH`, and the inner run's own chain head must equal the head the outer
run recorded for it.

- PASS: every recorded inner run whose folder was given matches its recorded head.
- FAIL: a recorded head differs from the inner run's actual chain head, or an inner run's folder was
  given but its manifest cannot be read (a damaged inner chain).
- NOT-RUN: no nested run was recorded, or no folder was given.

```
onetrace-verify --nested-run runs/<inner_run_id> runs/<outer_run_id>
```

## What this does not claim

- **Nesting is recorded for calls through decorated stages only.** A call that bypasses the
  decorator is not in the record, as today. `parent`, `children`, `parent_run` and `parent_stage`
  name the calls that went through `@ot.stage` and `@ot.run`, and nothing else.
- **A comparison does not descend into a stage called inside another stage.** It reports that stage
  as a first difference of its own, as shown above; it descends into a run started inside a stage
  only when both inner runs' folders are given.
