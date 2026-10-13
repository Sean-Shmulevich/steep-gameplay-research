# Idle task worker pool

## Identity and scope

Static inspection identifies a separate thread class through its installed table,
constructor and loop. The image contains the diagnostic strings `IdleThread %u`
and `::IdleThread::ThreadRun`. This pool is distinct from the ordinary scheduler
workers described in [worker context](WORKER_THREAD_CONTEXT.md). No live execution
or membership in a particular gameplay phase was observed.

The pool constructor allocates smaller thread objects, initializes an event holder
and a false stop byte, and installs a table whose loop slot targets this consumer.
The startup and exit slots are no-ops. The common thread entry remains shared with
the ordinary worker, including its startup notification. The constructor waits on
that shared startup holder after each launch before appending the thread pointer
to its own collection. Launch success, error handling and platform event behavior
remain separate unresolved contracts.

The diagnostic/default name is later passed through a naming helper, and the
configured execution mode becomes four. The common entry copies that mode to TLS;
this class's no-op startup hook does not overwrite it with ordinary-worker mode
six. Its loop writes one to another TLS field. The meaning of those numeric modes
is not established.

## Consumer control flow

The following pseudocode preserves inspected ordering. Helper names describe local
roles; the queue-pop algorithm is detailed below and callback producers remain open.

```text
idle_task_loop(thread):
    tls.task_loop_marker = 1
    entry_callback_ran = false
    if not thread.stop:
        repeat:
            wait_adapter(thread.event_holder)
            if not entry_callback_ran:
                callback = copy_optional_entry_callable(global_task_manager)
                if callback is present:
                    invoke_callable(callback)
                    entry_callback_ran = true
            repeat:
                node = pop_task_node(global_task_manager)
                if node == null:
                    break
                task = node.payload
                return_node_to_tagged_free_list(node)
                if task == null:
                    break
                task.execute_virtual()
                allocation_metadata = inspect_allocation(task)
                task.destroy_virtual(non_deleting_flag=0)
                release_task_allocation(task, allocation_metadata)
            until false
        until thread.stop
    callback = copy_optional_exit_callable(global_task_manager)
    if callback is present:
        invoke_callable(callback)
```

The entry callback retries on later wakeups if absent. After a present callback
returns normally, a local byte prevents calling it again. The exit callable is
looked up independently and may run even if the initial stop test skips the loop.
The callable copies mask low tag bits before invocation. Their signatures,
producers, lifetime guarantees and exception behavior remain unresolved.

The node goes back to the free list before the task's virtual execution. Node
lifetime and task lifetime therefore differ. The free-list update packs a pointer
in the lower 48 bits with an incremented 16-bit tag in the upper bits and retries
an atomic compare/exchange. This is observed tagging arithmetic, not a proof that
all ABA or reclamation hazards are excluded. The pop helper is decoded below.
A non-null node with a null payload ends this local drain attempt after returning
the node; it does not fall through to another pop.

## Stop and quiescence boundaries

The stop byte is checked before entering the loop and after draining, not before
each task. A stop request during a callback does not visibly interrupt that
callback. It also does not by itself prevent the next queued task from starting.
With continuing submissions, the local drain may not reach the next stop check.
The stop writer, wakeup producer and submission exclusion are still missing.

Ordinary job execution/outstanding counters do not account for this consumer's
virtual task calls in the inspected loop. No link to their completion accounting
is visible here. A future whole-engine pause contract must either establish this
pool's relevance and drain it, or prove that its tasks cannot touch the state being
modified. An ordinary scheduler drain alone cannot establish that proof.

The event field of this class occupies the offset used by the ordinary worker's
selection-bypass byte. That coincidence is not a type match. The initial search
also found a separate constructor writing a byte at the same offset; its different
table and layout do not establish a worker flag setter.

## Evidence and remaining joins

The table reference to this consumer matches the table installed by the inspected
pool constructor. The common entry and no-op hook slots were checked directly.
The constructor, consumer and table were inspected from image SHA-256
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
Protected event and thread-launch targets were not treated as recovered OS APIs.
No payloads, image bytes or live addresses are included.

Next joins are the manager's task submission path, stop-byte writer,
event notification and concrete task subclasses. This pool is not yet integrated
into the independent runtime; manufacturing its task graph would hide those gaps.


## Tagged dummy-node pop

A follow-up decoded the bounded leaf pop helper and the queue constructor. The
constructor obtains a node, stores it as both tagged head and tagged tail with
zero tags, and writes the queue's own identity into that node's next field. This
identity is the empty-link sentinel. It is not a null-next convention. Allocation
failure handling is not closed by this normal construction path.

```text
pop(queue):
    repeat:
        head = load(queue.tagged_head)
        tail = load(queue.tagged_tail)
        old_dummy = low48(head)
        next = load(old_dummy.next)
        if head != load(queue.tagged_head):
            continue
        if next == queue.identity:
            return null
        if old_dummy == low48(tail):
            later_next = load(low48(tail).next)
            proposed_tail = pack(low48(later_next), uint16(tag(tail) + 1))
            if low48(proposed_tail) != queue.identity:
                compare_exchange(queue.tagged_tail, tail, proposed_tail)
            continue
        payload = load(next.payload)
        proposed_head = pack(low48(next), uint16(tag(head) + 1))
        if compare_exchange(queue.tagged_head, head, proposed_head):
            old_dummy.payload = payload
            return old_dummy
```

The second head read validates only that tagged-head observation. The tail and
next loads are separate observations. In the tail-help branch the link is read
again; substituting the earlier `next` would erase a possible interleaving. Both
success and failure of tail assistance return to the start. Only successful head
advancement permits copying the payload and returning the old dummy. The next
node becomes the new dummy; its identity is not the node returned to the consumer.

[The executable decision helper](../../engine/tagged_task_queue.py) preserves these
branches with caller-supplied load observations and deferred CAS outcomes. It does
not read process memory, perform atomic operations or claim a complete queue.
Synthetic tests distinguish changed-head retry, empty sentinel, a changed link
between reads, lagging-tail assistance, old-dummy retirement, null payload and
16-bit tag wrap. Pointer words in tests are synthetic identities.

The shared manager factory now joins to this pool constructor and publishes its
returned pointer to the exact global read by the consumer. Publication happens
after the constructor has launched threads and waited for their startup
notifications. The consumer's first event wait precedes its first manager load;
this ordering is relevant to startup safety, but does not prove that an early
notification or another caller cannot race publication. The factory and consumer
alone do not establish the notification producer or exclusion contract.

The task submission/push path, reclamation contract and stop writers remain open.
Finite tag width and successful CAS do not by themselves prove memory lifetime
safety or determinism across native executions.
