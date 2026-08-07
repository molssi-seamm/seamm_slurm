Getting Started
===============

``seamm_slurm`` wraps the SLURM command-line tools (``sbatch``, ``squeue``,
``sacct``, ``scancel``) behind one interface, ``SlurmBackend``, with two
transports -- ``LocalSlurm`` (SLURM CLI on the current host) and
``SshSlurm`` (SLURM CLI on a remote host over passwordless SSH). It has no
SEAMM-core dependency and no notion of SEAMM's own job-status vocabulary; it
only speaks SLURM's.

Installing
----------

The library has no runtime dependencies::

    pip install seamm_slurm

Basic usage
-----------

.. code-block:: python

    from seamm_slurm import LocalSlurm, SshSlurm
    from seamm_slurm.script import build_script

    backend = LocalSlurm()
    # or, from a host that is not itself a SLURM submit host:
    # backend = SshSlurm("molssi10")

    script = build_script(
        {
            "job_name": "my-flowchart",
            "partition": "batch",
            "nodes": 1,
            "ntasks": 1,
            "time": "01:00:00",
            "chdir": "/home/psaxe/SEAMM/Jobs/projects/demo/Job_00123",
        },
        payload=(
            "source /home/psaxe/miniconda3/etc/profile.d/conda.sh\n"
            "conda activate seamm\n"
            "run_from_jobserver 123 "
            "/home/psaxe/SEAMM/Jobs/projects/demo/Job_00123 "
            "/home/psaxe/SEAMM/Jobs/seamm.db\n"
        ),
    )
    job_id = backend.submit(script)

    statuses = backend.poll_many([job_id])
    print(statuses[job_id].category)  # "pending" | "running" | "completed" | ...

See the design doc under :doc:`developer_guide/campaigns/2026-08-06/index`
for the full rationale, and the workspace-root
``~/Work/SEAMM/jobserver-slurm-plan.md`` living plan for how this fits into
the larger ``seamm_jobserver`` SLURM integration.
