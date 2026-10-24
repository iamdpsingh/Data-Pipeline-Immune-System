from spark.utils.metrics_accumulator import BatchMetrics


def test_clean_ratio():
    bm = BatchMetrics(total_records=100, valid_records=95, quarantined_records=5)
    assert bm.clean_ratio == 0.95
