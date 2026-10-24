# PySpark Batch Metrics Accumulator
from dataclasses import dataclass

@dataclass
class BatchMetrics:
    total_records: int
    valid_records: int
    quarantined_records: int

    @property
    def clean_ratio(self) -> float:
        return self.valid_records / max(self.total_records, 1)
