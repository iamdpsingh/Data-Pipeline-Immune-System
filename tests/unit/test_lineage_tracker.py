from spark.utils.lineage_tracker import capture_stage_lineage

def test_capture_lineage():
    res = capture_stage_lineage("silver_orders", ["source.json"], "gs://silver/orders", 100)
    assert res["stage"] == "silver_orders"
    assert res["records_processed"] == 100
