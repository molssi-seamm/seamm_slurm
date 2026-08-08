=======
History
=======

2026.8.8 -- Stage a job's files to/from a remote host with no shared filesystem
    * New ``LocalStager``/``RsyncStager`` (``seamm_slurm.stage``), paired with
      the existing ``LocalSlurm``/``SshSlurm`` transports: lets a JobServer
      that shares no filesystem with the SLURM submit host (e.g. a laptop
      reaching a cluster over ssh) push a job's working directory there
      before submission and pull results back after, over
      ``rsync -e ssh``. ``LocalStager`` is a no-op for the existing
      shared-storage case.
    * ``SlurmSection`` gained ``build_stager()`` (alongside
      ``build_backend()``) and three new optional ini keys:
      ``remote_root`` (base directory for a job's remote scratch tree),
      ``remote_run_from_jobserver`` (explicit absolute path to invoke on
      the remote host, preferred), and ``remote_conda_env`` (falls back
      to ``conda run -n <env>`` when the absolute path isn't known/stable).
    * Live-validated: a real job staged to a remote cluster over actual
      ssh/rsync, ran there for real, and staged back correctly.

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
