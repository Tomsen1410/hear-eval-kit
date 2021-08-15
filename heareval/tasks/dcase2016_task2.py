#!/usr/bin/env python3
"""
Pre-processing pipeline for DCASE 2016 task 2 task (sound event
detection).

The HEAR 2021 variation of DCASE 2016 Task 2 is that we ignore the
monophonic training data and use the dev data for train.
We also allow training data outside this task.
"""

import logging
from pathlib import Path
from typing import List

import luigi
import pandas as pd

import heareval.tasks.pipeline as pipeline

logger = logging.getLogger("luigi-interface")

config = {
    "task_name": "dcase2016_task2",
    "version": "hear2021",
    "embedding_type": "event",
    "prediction_type": "multilabel",
    "download_urls": [
        {
            "name": "train",
            "url": "https://archive.org/download/dcase2016_task2_train_dev/dcase2016_task2_train_dev.zip",  # noqa: E501
            "md5": "4e1b5e8887159193e8624dec801eb9e7",
        },
        {
            "name": "test",
            "url": "https://archive.org/download/dcase2016_task2_test_public/dcase2016_task2_test_public.zip",  # noqa: E501
            "md5": "ac98768b39a08fc0c6c2ddd15a981dd7",
        },
    ],
    # TODO: FIXME
    # Want different for train and test?
    "sample_duration": 120.0,
    "splits": [
        {"name": "train", "max_files": 10},
        {"name": "test", "max_files": 10},
        {"name": "valid", "max_files": 2},
    ],
    "small": {
        "download_urls": [
            {
                "name": "train",
                "url": "https://github.com/turian/hear2021-open-tasks-downsampled/raw/main/dcase2016_task2_train_dev-small.zip",  # noqa: E501
                "md5": "aa9b43c40e9d496163caab83becf972e",
            },
            {
                "name": "test",
                "url": "https://github.com/turian/hear2021-open-tasks-downsampled/raw/main/dcase2016_task2_test_public-small.zip",  # noqa: E501
                "md5": "14539d85dec03cb7ac75eb62dd1dd21e",
            },
        ],
        "version": "hear2021-small",
        "splits": [
            {"name": "train", "max_files": 100},
            {"name": "test", "max_files": 100},
            {"name": "valid", "max_files": 100},
        ],
    },
    # DCASE2016 task 2 used the segment-based total error rate as their main metric
    # and then the onset only event based F1 as their secondary metric.
    # However, we announced that we would use onset only event based F1 as primary.
    "evaluation": ["onset_only_event_based", "segment_based"],
}


class ExtractMetadata(pipeline.ExtractMetadata):
    train = luigi.TaskParameter()
    test = luigi.TaskParameter()

    def requires(self):
        return {"train": self.train, "test": self.test}

    """
    DCASE 2016 uses funny pathing, so we just hardcode the desired
    (paths)
    Note that for our training data, we only use DCASE 2016 dev data.
    Their training data is short monophonic events.
    """
    split_to_path_str = {
        "train": "dcase2016_task2_train_dev/dcase2016_task2_dev/",
        "test": "dcase2016_task2_test_public/",
    }

    def get_split_metadata(self, split: str) -> pd.DataFrame:
        logger.info(f"Preparing metadata for {split}")

        split_path = (
            Path(self.requires()[split].workdir)
            .joinpath(split)
            .joinpath(self.split_to_path_str[split])
        )

        metadatas = []
        for annotation_file in split_path.glob("annotation/*.txt"):
            metadata = pd.read_csv(
                annotation_file, sep="\t", header=None, names=["start", "end", "label"]
            )
            # Convert start and end times to milliseconds
            metadata["start"] *= 1000
            metadata["end"] *= 1000
            sound_file = (
                str(annotation_file)
                .replace("annotation", "sound")
                .replace(".txt", ".wav")
            )
            metadata = metadata.assign(
                relpath=sound_file,
                slug=lambda df: df.relpath.apply(self.slugify_file_name),
                subsample_key=lambda df: self.get_subsample_key(df),
                split=lambda df: split,
                split_key=lambda df: self.get_split_key(df),
                stratify_key=lambda df: self.get_stratify_key(df),
            )

            metadatas.append(metadata)

        return pd.concat(metadatas)


def main(
    num_workers: int,
    sample_rates: List[int],
    luigi_dir: str,
    tasks_dir: str,
    small: bool = False,
):
    if small:
        config.update(dict(config["small"]))  # type: ignore
    config.update({"luigi_dir": luigi_dir})

    # Build the dataset pipeline with the custom metadata configuration task
    download_tasks = pipeline.get_download_and_extract_tasks(config)

    configure_metadata = ExtractMetadata(
        outfile="process_metadata.csv", data_config=config, **download_tasks
    )
    final = pipeline.FinalizeCorpus(
        sample_rates=sample_rates,
        tasks_dir=tasks_dir,
        metadata=configure_metadata,
        data_config=config,
    )

    pipeline.run(final, num_workers=num_workers)
