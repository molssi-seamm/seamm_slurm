=======
History
=======

Unreleased
    * Initial scaffold: ``SlurmBackend`` (submit/poll_many/cancel),
      ``LocalSlurm`` and ``SshSlurm`` transports, JSON-with-text-fallback
      parsing for ``squeue``/``sacct`` (SLURM versions differ in ``--json``
      support), and ``script.build_script()`` for turning a directives dict
      into a full ``sbatch`` script. Not yet released or wired into
      ``seamm_jobserver``.
