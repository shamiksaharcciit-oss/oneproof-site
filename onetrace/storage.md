# Storage: a run in a bucket

A run folder is immutable files whose integrity is in the files themselves — the chain, the
digests, the signature. So a finished run can live in an S3-compatible bucket, apart from any
console, and a reader verifies it on every read. The bucket **verifies nothing; the reader does.**

The client is the optional `onetrace[s3]` extra. Without it, an `s3://` destination is refused,
naming the extra; a local destination needs none of it.

## Sending a run to a bucket

Name the destination with `ONETRACE_RUNS`, so a deployment turns it on without changing the code:

```
ONETRACE_RUNS=s3://my-bucket/runs  python pipeline.py
```

or on the run itself:

```python
@ot.run(runs="s3://my-bucket/runs")
def main():
    ...
```

`Recorder(runs=…)` does the same. A local path there (or none) writes runs locally as always.

The run is **written and sealed locally first**, exactly as a local run is. When it closes, the
sealed folder is uploaded, **the manifest last**, so the last byte to reach the bucket is the one
that names the chain head: a reader sees a whole run or no run, never half of one. Each object's
checksum is set to the file's sha256 — the S3 checksum header where the endpoint stores one, else a
`<key>.sha256` sidecar beside the object.

The manifest gains a `sink` member saying whether the upload was delivered:

```json
"sink": {"delivered": "true", "objects": "7"}
```

The **bucket, the endpoint and the credentials are never recorded.** The client reads its
credentials from its own environment and credential files (the standard ones the S3 client uses),
never from onetrace's own configuration; onetrace records no credential and no endpoint in the run.

A run with no sink writes the same bytes it always did: the `sink` member is absent, and the record
format is unchanged.

## The index object

Beside the runs, one small object per run — `<prefix>/_index/<run id>.json` — carries the run id,
the pipeline, the chain head, the first step's instrument, the run's time, the verdict it recorded
(when it recorded one) and the kept-files count. A console lists runs from these without fetching a
whole folder.

## When the upload does not go through

A failed upload never loses the run: it is **recorded, not silent.** The failure is reported on
stderr and in the manifest's `sink` member, and the local folder stays:

```json
"sink": {"delivered": "false", "objects": "0", "note": "the run was not delivered",
         "reason": "EndpointConnectionError"}
```

Upload it later, from where it was recorded:

```
onetrace sink retry ./runs/<run id>
```

`sink retry` reads the destination from a `.sink` file beside the folder (a local operational file,
not part of the record and never uploaded), or takes `--to s3://bucket/prefix`. A delivered run's
local copy stays unless `--sink-remove` is given.

## Reading a run back

Verify a run in the bucket as you would a local one:

```
onetrace sink verify s3://my-bucket/runs/<run id>
```

It fetches the run into a temporary folder, checks each object against its stored checksum or its
`.sha256` sidecar, and runs the verifier over it, reporting as the verifier does. `onetrace-verify`
itself stays file-only: it reads a folder, never a bucket.

## Streaming into the same bucket

A run may stream its receipts to the same bucket as they are produced
(`stream_to="s3://my-bucket/runs"`, or `ONETRACE_STREAM_TO`), so a run interrupted partway still
leaves its partial chain in storage. A streamed receipt is written under the run's own prefix,
**byte-identical to the one the sealed upload carries.** See [streaming](streaming.md).

## Lifecycle lives in the bucket, not in onetrace

The runs are plain objects, so the bucket's own lifecycle rules — not onetrace — move old runs to
colder storage, or delete them, when a team decides. A team can keep the small receipts for years
and let the larger kept inputs and outputs expire sooner, by prefix; the verifier reads a run whose
kept files are gone as "outputs not kept", a verdict it already knows. onetrace writes the runs and
reads them; it does not manage the bucket.

## What the sink does not claim

- **A bucket verifies nothing; the reader verifies on every read.** Storage location does not change
  what a record proves. A tampered object is caught when a reader verifies the run, not at rest.
- **A delivered run is the same record as the local one.** The sink uploads the sealed folder and
  changes no receipt; the only addition is the manifest's optional `sink` member, which names no
  endpoint and no credential.
- **An object's checksum guards the transfer, not the record.** The chain, the digests and the
  signature are what prove the run; the per-object sha256 only catches an object damaged in the
  bucket, on the way back.
