# GenomicPipelineScheduler - extracted from termo2.py
"""
NLP2CMD - Przykłady zastosowań w różnych dziedzinach.

Ten moduł zawiera praktyczne przykłady użycia NLP2CMD
w IT, nauce i biznesie.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from genomic_sample import GenomicSample
from pipeline_step import PipelineStep

class GenomicPipelineScheduler:
    """
    Scheduler dla pipeline'u analizy genomowej.
    """

    def __init__(self,
                 samples: list[GenomicSample],
                 steps: list[PipelineStep],
                 total_cores: int = 64,
                 total_memory_gb: int = 256):
        self.samples = samples
        self.steps = steps
        self.total_cores = total_cores
        self.total_memory_gb = total_memory_gb

    def estimate_time(self, sample: GenomicSample, step: PipelineStep) -> float:
        """Szacowany czas wykonania kroku."""
        return step.time_per_gb * sample.size_gb

    def schedule(self) -> dict:
        """Zaplanuj wykonanie pipeline'u."""
        # Uproszczony scheduler - w produkcji użyj Langevin sampling
        schedule = []
        current_time = 0

        for sample in sorted(self.samples, key=lambda s: s.priority):
            sample_schedule = {'sample': sample.id, 'steps': []}
            step_end_times = {}

            for step in self.steps:
                # Znajdź najwcześniejszy możliwy start
                start_time = current_time
                for dep in step.depends_on:
                    if dep in step_end_times:
                        start_time = max(start_time, step_end_times[dep])

                duration = self.estimate_time(sample, step)
                end_time = start_time + duration

                sample_schedule['steps'].append({
                    'step': step.name,
                    'start': start_time,
                    'end': end_time,
                    'duration': duration,
                })

                step_end_times[step.name] = end_time

            schedule.append(sample_schedule)

        return schedule
