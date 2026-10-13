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
roles; the queue-pop algorithm and callback producers are not decoded here.

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
all ABA or reclamation hazards are excluded. The pop helper needs separate study.
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

Next joins are the manager's task submission path, task-node pop, stop-byte writer,
event notification and concrete task subclasses. This pool is not yet integrated
into the independent runtime; manufacturing its task graph would hide those gaps.
