# Evidence conventions

Keep these distinctions when using or extending the research:

- **Authored data:** values or references decoded from a resource. This does not prove runtime selection or physical units.
- **Static finding:** a branch, formula, assignment, or ownership relationship inspected in the analyzed image. Conditional receiver/type assumptions remain part of the claim.
- **Byte verification:** selected exported instructions matched the local analyzed image. This establishes consistency of those artifacts, not completeness or runtime execution.
- **Live observation:** recorded values under stated process/owner guards. Sequential reads are not atomic and guards do not pin object lifetime or prove freedom from address reuse.
- **Derived calculation:** a result calculated from a stated model and parameters. It is not automatically an independent measurement.
- **Illustrative pseudocode:** an explanation of known local operations. An unresolved call or input remains explicit.
- **Hypothesis or lead:** a candidate requiring further tracing or an experiment.

Historical evidence notes include function addresses and resource identifiers so another researcher can identify the same paths. Addresses are build-specific. Do not copy them into another build or reuse a prior process's absolute heap pointers.

The source image, raw instruction exports, memory reads and verification scripts are intentionally excluded from this public package. As a result, this repository describes verification performed in the original workspace but cannot independently reproduce those binary checks by itself.

[SOURCE_MANIFEST.json](../SOURCE_MANIFEST.json) records original research-document paths and hashes plus the published text hashes. Publication adds explanatory banners, removes machine-specific home paths, and remaps links. It does not silently upgrade evidence strength. Links to omitted files are rendered as explicit local-artifact references.

When two reports conflict, retain the contradiction until a later report provides the resolving evidence. A newer date alone does not prove a claim. The [status page](STATUS.md) identifies the important reconciled corrections.
