#!/usr/bin/env python3
"""
Runs a luigi pipeline to build a dataset
"""

import logging
import multiprocessing
from typing import Optional

import click

import heareval.tasks.dcase2016_task2 as dcase2016_task2
import heareval.tasks.nsynth_pitch as nsynth_pitch
import heareval.tasks.speech_commands as speech_commands
import heareval.tasks.pipeline as pipeline

logger = logging.getLogger("luigi-interface")

tasks = {
    "speech_commands": [speech_commands],
    "nsynth_pitch": [nsynth_pitch],
    "dcase2016_task2": [dcase2016_task2],
    "all": [speech_commands, nsynth_pitch, dcase2016_task2],
}


@click.command()
@click.argument("task")
@click.option(
    "--num-workers",
    default=None,
    help="Number of CPU workers to use when running. "
    "If not provided all CPUs are used.",
    type=int,
)
@click.option(
    "--sample-rate",
    default=None,
    help="Perform resampling only to this sample rate. "
    "By default we resample to 16000, 22050, 44100, 48000.",
    type=int,
)
@click.option(
    "--tmp-dir",
    default="_workdir",
    help="Temporary directory to save all the intermediate tasks (will not be deleted afterwords)",
    type=str,
)
@click.option(
    "--tasks-dir",
    default="tasks",
    help="Directory to save the final task output",
    type=str,
)
@click.option(
    "--small",
    is_flag=True,
    help="Run pipeline on small version of data",
    type=bool,
)
def run(
    task: str,
    num_workers: Optional[int] = None,
    sample_rate: Optional[int] = None,
    tmp_dir: Optional[str] = "_workdir",
    tasks_dir: Optional[str] = "tasks",
    small: bool = False,
):

    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
        logger.info(f"Using {num_workers} workers")

    if sample_rate is None:
        sample_rates = [16000, 22050, 44100, 48000]
    else:
        sample_rates = [sample_rate]

    tasks_to_run = [
        task_script.main(  # type: ignore
            sample_rates=sample_rates,
            tmp_dir=tmp_dir,
            tasks_dir=tasks_dir,
            small=small,
        )
        for task_script in tasks[task]
    ]

    pipeline.run(
        tasks_to_run,
        num_workers=num_workers,
    )


if __name__ == "__main__":
    run()
