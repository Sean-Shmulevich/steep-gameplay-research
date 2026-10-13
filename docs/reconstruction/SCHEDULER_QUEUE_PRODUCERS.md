# Queue producers: worker count, category and affinity routing

The selection score's shared default is written during scheduler worker creation. The same initialization builds worker masks. Enqueue uses the job's category and lowest required-mask bit to choose a worker-local or shared container. These are concrete producers for inputs previously left configurable in [queue eligibility](SCHEDULER_QUEUE_ELIGIBILITY.md).

## Shared default comes from worker initialization

The inspected initialization caller reads a configuration object's worker-count field, applies an unsigned lower bound of one, then passes that count to the scheduler initializer. The initializer again applies an unsigned lower bound of one and clamps against a separate global upper bound.

```text
requested = max_unsigned(configuration.worker_count, 1)
selected = min_unsigned(max_unsigned(requested, 1), global_upper_bound)
shared_default = selected
another_count = selected
auxiliary_count = max_signed(int32(selected - 1), 1)
```

This preserves the comparison directions. The upper bound's producer and valid range remain unresolved. If that bound is zero, the local clamp can still yield zero; no claim of unconditional positivity follows from the lower-bound operation alone.

The analyzed image contains `INT_MAX` in the shared-default field before considering this initializer. That value is evidence of the image contents, not the live configured worker count. Jobs that replace an `INT_MAX` limit with the shared default are using the initialized count on the ordinary configured path.

The initializer allocates one worker object per selected count, appends it to the worker array and calls its setup routine with its index. Thus the association with worker count is established by the loop, not just by the global field's later use in scoring.

## Worker mask producer

The initialization loop starts a 32-bit mask at one and rotates it left by one after each worker:

```text
mask = uint32(1)
for index in range(selected):
    worker = construct_worker()
    worker.index = index
    worker.mask = mask
    append_worker(worker)
    configure_worker(worker, index, other_arguments)
    mask = rotate_left_32(mask, 1)
```

For the first 32 workers, the mask is a distinct single bit. Rotation wraps after 32; this pass does not prove that configured counts above 32 are reachable or supported. Replacing rotation with an unbounded shift would invent different behavior.

## Job construction supplies category and zero masks

The common job constructor stores its category argument and zeroes the adjacent required/excluded mask pair. It initializes execution and outstanding-dispatch counts to zero.

Its initial limit calculation zero-extends a byte-sized caller argument and compares it with the signed int32 shared default. A follow-up instruction check establishes signed less-or-equal selection, followed by byte truncation. For ordinary defaults within the byte range, the resulting byte-sized value is the smaller of those inputs. The decoded implementation truncates the selected result to a byte before storing it as the job limit. Later concrete constructors and setup routines may overwrite that limit, so this base initialization is not a universal final limit.

```text
construct_base_job(category_argument, byte_limit_argument):
    job.category = category_argument
    job.required_mask = 0
    job.excluded_mask = 0
    job.limit = uint8(min_signed(zero_extend(byte_limit_argument), int32(shared_default)))
    job.executions = 0
    job.outstanding_dispatches = 0
```

The constructor does not validate category against the three categories traversed by the ordinary selector. Its caller contract matters. This pass does not assign category names or recover every later mask setter.

## Enqueue chooses local or shared storage

Enqueue reads the category and required mask. For a nonzero required mask it finds the least significant set bit and uses that bit index to read the scheduler's worker array. If that pointer is non-null it selects that worker's local queue for the category. Otherwise, or when the required mask is zero, it selects the shared queue for that category.

```text
enqueue(scheduler, job):
    category = signed(job.category)
    queue = scheduler.shared[category]
    if job.required_mask != 0:
        index = least_significant_set_bit(job.required_mask)
        worker = scheduler.workers[index]
        if worker is not null:
            queue = worker.local[category]

    lock(queue)
    insert_job_pointer(queue, job)
    job.state = SCHEDULED
    if job.limit == INT_MAX:
        job.limit = shared_default
    atomic_add(scheduler.aggregate_limit, job.limit)
    unlock(queue)
    scheduler.change_counter += 1
```

There is no explicit worker-array bounds check in the inspected lookup. Valid mask construction is therefore an unresolved input invariant. The excluded mask does not participate in this enqueue choice.

This explains the ordinary selector's local-queue flag: enqueue already routes a required-mask job to a specific worker by its lowest set bit, and the local selector omits the shared affinity tests. It does not establish that arbitrary caller-supplied masks are safe or that every eligible bit can receive that job.

## Pointer insertion order

When a job's front-insertion flag is clear, enqueue grows the pointer array if needed, increments its count and writes the job at the old end. When the flag is set, it calls an insertion helper with index zero, then writes the job pointer into the first slot and increments a separate scheduler counter.

The helper's full shifting contract was not independently decoded here, so the strongest local facts are the zero insertion argument and explicit first-slot store. The normal append path is fully visible. Array order matters because selection keeps the earlier candidate on score ties and exits at the first zero score.

## Remaining scope and verification

The worker initializer, its configuration caller, common job constructor and enqueue routine were freshly decoded from the analyzed image. SHA-256: `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.

Still open are the upper-bound producer, configuration field's external name and default, later category/mask setters, valid mask/count constraints, and all other job-type overrides. These findings support a configurable worker-count producer and explicit queue routing in the independent model. They do not justify hard-coding the image's `INT_MAX` value as an operational concurrency count. No game execution, attachment or emulation was used.

## Base-limit comparison follow-up

The constructor loads the argument with byte zero-extension and compares that
32-bit value against the default. It first prepares the default's low byte, then
uses signed less-or-equal conditional selection to substitute the argument.
Finally it zero-extends the selected low byte into the limit field. MOVZX does
not alter the comparison flags. Equivalent mathematics is signed minimum
followed by uint8 conversion, not an unsigned minimum or a signed final limit.

For example, argument 255/default 256 produces 255, while argument 0/default -1
produces 255. Argument 255/default -256 produces zero. These boundary evaluations
do not establish that negative operational defaults occur in the game.
`base_job_limit` in `engine.queue_producers` implements this rule with explicit
uint8/int32 inputs. Later concrete constructors may still override it.
