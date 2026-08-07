2026-08-06 -- Initial scaffold
===============================

Status (2026-08-06, later)
---------------------------

Wired into ``seamm_jobserver``'s whole-flowchart SLURM submission mode and
validated end-to-end against a real cluster (MolSSI10), isolated from its
live production JobServer: real ``sbatch``-to-completion runs, a genuine
resubmit-and-give-up sequence under repeated real SLURM failures, and a
deterministic kill/restart test confirming reattachment resumes a still-live
SLURM job without duplicate submission. One correction to the design below:
no conda activation turned out to be needed in the sbatch payload after all
(see "Not in this package").

Scope
-----

``seamm_slurm`` is Phase 1 of the ``seamm_jobserver`` SLURM-integration plan
(full plan: ``~/Work/SEAMM/jobserver-slurm-plan.md``, a workspace-root living
doc, not packaged). That plan calls for two long-term submission models
("Option 1": JobServer submits a whole flowchart run as one SLURM job;
"Option 2", future: ``seamm_exec`` submits individual heavy codes per step)
sharing one SLURM-talking backend, rather than duplicating ``sbatch``/
``squeue``/``sacct`` handling in each consumer. This package is that shared
backend.

Design points
-------------

- **Two transports behind one interface.** ``LocalSlurm`` runs the SLURM CLI
  directly (the process is on a SLURM submit host, e.g. a cluster head/login
  node). ``SshSlurm`` runs the identical commands on a remote host over
  passwordless SSH. Both subclass ``SlurmBackend`` and only need to
  implement ``_run(argv, input_text) -> (returncode, stdout, stderr)`` --
  all submit/poll/cancel logic and JSON-vs-text parsing lives once, in the
  base class.
- **JSON when available, text parsing otherwise, decided per-backend at
  runtime.** Confirmed during Phase 0 groundwork that this is a real, not
  hypothetical, need: ChemAI runs SLURM 21.08.5 (``squeue --json``/
  ``sacct --json`` both work, OpenAPI v0.0.37); MolSSI10 runs SLURM 20.11.4
  (``--json`` unrecognized on both commands). ``SlurmBackend`` probes once
  per command per backend instance and remembers the result.
- **``sacct``'s and ``squeue``'s JSON schemas are not analogous** --
  confirmed against real completed jobs on ChemAI. ``squeue --json``'s
  ``job_state`` is a flat string (``"COMPLETED"``). ``sacct --json``'s
  ``state`` is a nested object (``{"current": "COMPLETED", "reason": ...}``),
  and its ``exit_code`` is similarly nested
  (``{"status": "SUCCESS", "return_code": 0}``). The two JSON parsers are
  separate for this reason, not just for the different field sets.
- **Submission is filesystem-agnostic by construction.** ``submit()`` takes
  the full script text and pipes it to ``sbatch --parsable`` on stdin --
  never needs the script to exist as a file the target host can read. This
  sidesteps a real Phase-0 finding: there is no shared filesystem between
  this Mac and either cluster host, so a submitted job's script can't simply
  be "the same file" the caller wrote locally, whether that be the future
  ``SshSlurm`` cross-host case or a caller (like a JobServer) that just
  wants to submit without worrying about where the target host will look
  for a file.
- **No SEAMM-status vocabulary here.** ``JobStatus.category`` classifies a
  SLURM job as one of ``pending``/``running``/``completed``/``cancelled``/
  ``failed``/``unknown`` -- a SLURM-domain concept, not a SEAMM one. Mapping
  that to ``seamm_jobserver``'s own ``jobs.status`` column values
  (``submitted``/``running``/``finished``/...) is Phase 2's job, done in
  ``seamm_jobserver`` itself, keeping this package genuinely reusable
  (including, later, by ``seamm_exec``, per Option 2).
- **``poll_many()`` batches.** One ``squeue`` call plus (for anything squeue
  no longer lists) one ``sacct`` call per polling cycle, not one call per
  tracked job -- matters once a JobServer instance is tracking many
  outstanding jobs.

Not in this package
--------------------

- Building the actual sbatch payload for a SEAMM flowchart run (the
  ``run_from_jobserver`` invocation -- no conda activation needed, since it's
  invoked by its full absolute path and SLURM inherits the submitting
  environment) -- that's ``seamm_jobserver``'s job (Phase 2), using
  ``script.build_script()`` from here for the ``#SBATCH`` boilerplate.
- The ``<root>/<jobserver-name>.ini`` config file and its multi-section
  (multi-cluster) routing -- also Phase 2/``seamm_jobserver``.
- A generic multi-scheduler abstraction (PBS/LSF/etc.) -- the config format
  this package's caller uses leaves room for a ``type =`` key per cluster
  section, but no non-SLURM backend is implemented or planned here yet.
