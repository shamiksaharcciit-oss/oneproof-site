# Variation: repeat runs and the profile

Monitoring shows where runs depart; it does not make a step repeatable. These two things help a
team see where variation enters, and whether a fix holds.

## Repeat-run sets

Record several runs of the same input as a set, so they can be read together:

```python
@ot.run(repeat_of=RUN_ID)          # this run repeats RUN_ID; Recorder(repeat_of=…) does the same
def main():
    ...
```

or run a command N times and link the runs it writes:

```
onetrace repeat -n N --runs-root DIR -- CMD…
```

The first run is the set's anchor; runs 2…N are started with `ONETRACE_REPEAT_OF` set to the
anchor's id, so each records the manifest member `repeat_of`. A run that repeats another records
`repeat_of`; a run that repeats nothing records nothing new, and is byte-identical to before.

## A step that may vary

A step may declare that its output is expected to differ between runs:

```python
@ot.stage("plan", instrument=…, may_vary=True)
def plan(…):
    ...
```

The declaration is recorded on the receipt (`may_vary`) and shown by the profile. It is never used
to hide a difference: a `may_vary` step that differs is still counted and still named.

## The profile

```
onetrace profile RUN…
```

reads a set of two or more runs and shows, per step, how often its output differs across the set
and of what kind:

- the runs are grouped by their output digests; the largest group is the set's common output, and a
  run outside it is one whose output differs;
- each differing run is classified against the common group: its **setting differs**, its **input
  differs**, or neither — **output only**, which the step is then marked **"varies on its own"**
  for (the question "does it differ even when nothing changed?").

Counts only; no score or grade.

## Whether a fix holds

After a change meant to make a step repeatable (a pinned seed, temperature 0, a fixed prompt, a
cached tool result), re-run the set and read the two profiles side by side:

```
onetrace profile --before SET… --after SET…
```

It shows, per step, how often the output differed before and after (for example, `plan`: 4 of 5
before, 0 of 5 after), and **names the setting that changed between the sets**. It does so as a
comparison does: it names the setting; it does not say the change made the difference.

A step that now matches across its repeats can be given an exact-match rule in a
[reference](references.md); one that still varies keeps a mask, declared, never guessed.

## What a profile does not claim

- A profile describes the repeats recorded, not every future run.
- Matching in N repeats does not prove a step is deterministic.
