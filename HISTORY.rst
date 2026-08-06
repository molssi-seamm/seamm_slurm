=======
History
=======

Unreleased
    * Initial scaffold: ``SlurmBackend`` (submit/poll_many/cancel),
      ``LocalSlurm`` and ``SshSlurm`` transports, JSON-with-text-fallback
      parsing for ``squeue``/``sacct`` (SLURM versions differ in ``--json``
      support), and ``script.build_script()`` for turning a directives dict
      into a full ``sbatch`` script.
    * Now wired into ``seamm_jobserver``'s whole-flowchart SLURM submission
      mode and validated end-to-end against a real cluster: real
      ``sbatch``-to-completion runs, a genuine resubmit-and-give-up sequence
      under repeated real SLURM failures, and a deterministic kill/restart
      test. Not yet released to PyPI.
