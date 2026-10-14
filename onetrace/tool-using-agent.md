# Recording a tool-using agent

An agent that calls a model, lets the model ask for a tool, runs the tool and calls the model again
is a pipeline whose steps repeat. onetrace records it the same way as any other: `@ot.run` on the
function that does the whole job once, and `@ot.stage` on each step. This page shows the shape with
a stand-in model and an invented order table, so it runs with no network calls and no real data,
then says what to decide for a real one.

## The example

Save this as `agent.py`:

```python
import onetrace as ot

ORDERS = {"A-100": "shipped", "A-101": "waiting for stock"}    # invented; your own system goes here


def stand_in_model(question, tool_result):
    """In place of a hosted model: asks for the order once, then answers from the tool's result."""
    if tool_result is None:
        return {"tool": "order_status", "order_id": "A-101"}
    return {"text": f"Order A-101 is {tool_result}."}


@ot.stage("model", instrument=ot.pkg("stand-in-model", "onetrace", kind="model-call"),
          repeats=True, output_trust="model-generated")
def call_model(question, tool_result=None):
    reply = stand_in_model(question, tool_result)
    ot.constant("model", "stand-in-model")
    return reply


@ot.stage("tool", instrument=ot.pkg("order-status", "onetrace", kind="tool"),
          repeats=True, output_trust="operator-authored")
def run_tool(request):
    return ORDERS.get(request["order_id"], "not found")


@ot.run(stages=["model", "tool"], trust="externally-sourced")
def agent(question):
    reply = call_model(question)
    while "tool" in reply:
        result = run_tool(reply)
        reply = call_model(question, result)
    return reply["text"]


if __name__ == "__main__":
    print(agent("Where is my order A-101?"))
```

Run it and check the record:

```bash
python agent.py
onetrace-verify --require-artifacts runs/<run_id>
```

The run folder holds four stages: `intake` (the question), `model#1`, `tool#1` and `model#2`.
`repeats=True` lets a stage run more than once in a run, numbering the calls.

## How the steps link

Stages link only when the same object is passed on whole (manual, section 16.1). Here:

- `run_tool(reply)` is given the model's whole reply, so `tool#1` records an edge from `model#1`.
  Passing `reply["order_id"]` instead would record the id as an ordinary input, with no edge.
- `call_model(question, result)` is given the tool's whole return value, so `model#2` records an
  edge from `tool#1`.

Keep each step's output whole when you pass it on, and take the part you need inside the next step.

## Trust classes

Each value a stage reads, and each value it returns, has a trust class: where the data came from.
onetrace never guesses one: an unstated class is recorded as `externally-sourced` and listed as
undeclared on that stage. In an agent:

- **What a user typed** is `externally-sourced`, never `operator-authored`. Here `@ot.run`'s
  `trust="externally-sourced"` records the question that way.
- **What a model wrote** is `model-generated`: `output_trust="model-generated"` on the model step.
  That includes the model's request for a tool.
- **What a tool returns** depends on the tool, and is a person's answer to give. A lookup in a
  system you run, as here, is `operator-authored`; a web page, a search result or another party's
  API is `externally-sourced`.

A tool that reads a file or a fetched page records it with its own class, through the running
stage's context:

```python
from onetrace.emit import current_stage

@ot.stage("fetch", instrument=ot.pkg("fetch", "onetrace", kind="tool"), output_trust="externally-sourced")
def fetch(path):
    raw = current_stage().read_external(path, "text/html", name="page", trust_class="externally-sourced")
    return raw.decode("utf-8")
```

`read_external` records the file's digest, its media type and the class you give; the file itself
is not stored. `trust_class="secret"` is refused before anything is digested: keep keys and tokens
out of every stage's arguments (manual, section 5.4).

## Comparing runs with a hosted model

A hosted model can answer differently to the same prompt, and its provider can change it without a
new name. Expect two runs of an agent to differ first at the model step, even when nothing you
control changed.

- **Record what you know about the model** with `ot.constant()`: its name or version, and the
  settings you send, including any you learn only from the reply. A comparison names a setting
  only when it was recorded this way (manual, sections 10.5 and 16.14).
- **Leave `rederivable` unstated** for a hosted model's step: it is recorded as not re-runnable,
  which is what a hosted model is.
- **Test the rest of the agent with a stand-in model**, as above. With the model fixed, two runs
  differ only where your code, your tools or their data differ, and `onetrace diff` names the
  first such step.
- **The console's Compare page looks past a varying model step.** When the first difference is a
  step marked not re-runnable and nothing recorded about it changed except its output, the page
  also names the first later step with a recorded change, marked "First recorded change".

## What this record does not show

- That the agent's answer was correct, or why the model wrote what it wrote.
- Anything a tool did that is not in its recorded inputs and outputs, or any step not decorated.
