# Documentation claim auditor

Version 0.1.0. An offline, deterministic, standard-library-only checker for
claims about cutting a rectangular region out of a picture. Supports CPython
3.9 or newer. No LLM, network, telemetry, or filesystem writes during scans.

## Install and run

```sh
python3 -m pip install .
image-cropping-claim-audit --version
image-cropping-claim-audit audit .
python3 -m image_cropping_claim_audit audit --ignore vendor/ . --json
image-cropping-claim-audit audit . --verbose --fail-on medium
python3 -m unittest discover
python3 -m build
```

The repository defaults to the current directory. Repeat the single-value
ignore option to skip multiple path prefixes. Verbose decisions go to stderr;
JSON output is an array of findings, each with rule, verdict, and message fields.
Exit status is 0 when no finding reaches the threshold, 2 when a finding does,
and 1 for usage or IO errors. The default threshold is high.

## Scope and decisions

The checker reads root README.md and Markdown files below docs/. Triple-backtick
fences are excluded; inline code remains prose. Denial spans are removed before
positive matching. Matching is case insensitive and uses exact substrings without
stemming, fuzzy matching, or hyphen normalization. Longest-first matching blanks
each matched span so an occurrence matches once under its longest phrase.

Source evidence comes from AST checks within each individual module. Import
aliases are resolved; local function and class definitions shadow route names.
Supported routes are a Pillow-loaded object followed by a region method, Pillow's
border-removal operation, a bounded slice of an OpenCV-loaded array, a scikit-image
utility call, a torchvision transform construction followed by an instance call,
a torchvision functional call, or one of 24 generic method/imported-function names.
Imports, uncalled references, strings, comments, external subprocesses, and parts
split across modules do not establish evidence. Virtual environments, Git metadata,
and bytecode caches are excluded. Invalid source syntax supplies no evidence.

Each rule family produces at most one finding. A positive documentation assertion
without evidence is HIGH. A denial contradicted by evidence is HIGH. An assertion
confined to test fixtures without evidence is MEDIUM, so it fails only at the medium
threshold. A denial without source evidence passes. A repository with no assertions
passes. The bundled oracle fixtures intentionally produce a MEDIUM result when
scanning this entire project; checking this README alone passes.

```text
documented-image-cropping-claim-false
documented-no-image-cropping-claim-false
```

## Differentiation

This tool checks cutting a rectangular region out of a picture. The following
neighbor checks have different responsibilities, listed in the same order:

```text
image-resizing-claim-audit
image-background-removal-claim-audit
image-object-detection-claim-audit
image-stitching-claim-audit
super-resolution-claim-audit
image-inpainting-claim-audit
image-colorization-claim-audit
```

- Changing a picture's pixel dimensions.
- Cutting a subject out of a picture.
- Finding and boxing things in one picture.
- Joining overlapping pictures into one wide picture.
- Model-based upscaling of one picture.
- Filling a hole in one picture.
- Adding color to a grey picture.

Those operations alone do not establish the checked capability. Rotation and
flipping alone do not establish it either.

## Limitations

Static pattern matching is not semantic judgement. Exact phrases cannot recognize
arbitrary restatements. Longest-first matching makes each occurrence match once
under its longest phrase. The first phrase below can also describe agricultural
pictures of agricultural crops; the second can name a standard augmentation transform, which may
be a training pipeline step rather than a shipped feature. Both still match.

```text
crop images
center crop
```

A region slice on an OpenCV-loaded non-picture array still counts because the
slice form is shared. The following fitting operation also cuts a region, but is
assigned to the neighbor's dimension-changing check. The generic call below counts
even on an unrelated object because its method name is shared.

```text
cv2
ImageOps.fit
unrelated.crop_image(...)
```

Tracing is module-local and syntactic, without runtime execution, control-flow
proof, dynamic dispatch resolution, or cross-module data flow. Evidence shows a
recognized pattern exists; it does not prove a working, reachable, shipped feature.

MIT licensed. The source distribution includes the runnable unittest suite.
