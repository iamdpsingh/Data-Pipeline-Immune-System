# PySpark Execution Lineage & Audit Tracker
from datetime import UTC, datetime


def capture_stage_lineage(
    stage_name: str, input_files: list, output_path: str, row_count: int
) -> dict:
    return {
        "stage": stage_name,
        "inputs": input_files,
        "output": output_path,
        "records_processed": row_count,
        "captured_at": datetime.now(UTC).isoformat(),
    }
