=======
History
=======

2026.8.6.1 -- Add seamm_slurm.config: ini parsing, moved from seamm_jobserver
    * ``SlurmSection``/``load_slurm_config`` (previously
      ``seamm_jobserver.slurm_config``) now live here, so any
      dependency-light consumer -- a future job-submission UI, for instance
      -- can read/validate a JobServer's ``<root>/<jobserver-name>.ini``
      without pulling in the rest of the SEAMM stack.
    * Added an optional ``[<section>.limits]`` companion ini section and
      ``SlurmSection.merge_overrides()``: sites can now say which SLURM
      directives a job may override per-job, and within what bounds
      (enumerated choices, or numeric/size/time ranges). Secure by default
      -- no ``.limits`` section means nothing is overridable.

2026.8.6 -- Initial release
    * ``SlurmBackend`` (submit/poll_many/cancel), ``LocalSlurm`` and
      ``SshSlurm`` transports, JSON-with-text-fallback parsing for
      ``squeue``/``sacct`` (SLURM versions differ in ``--json`` support), and
      ``script.build_script()`` for turning a directives dict into a full
      ``sbatch`` script.
    * Wired into ``seamm_jobserver``'s whole-flowchart SLURM submission mode
      and validated end-to-end against a real cluster: real
      ``sbatch``-to-completion runs, a genuine resubmit-and-give-up sequence
      under repeated real SLURM failures, and a deterministic kill/restart
      test.
