# Selected contact observations

`contact_return.json` contains 27 selected groups from a 767-group passive capture. It retains relative time/translation, velocity and contact fields. Pointers, raw bytes, host identity and absolute game position were removed. The source hash and selection rule are in the file.

Rows are not uniformly sampled. Full-capture cadence metrics are retained as metadata, not recomputed from this selection. Reads were non-atomic and input alignment was not verified. This is a small measured observation dataset, not an asset, save, memory dump or deterministic replay fixture. Stored runtime units are labeled without upgrading them to meters or seconds.
