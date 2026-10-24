from scripts.replay_quarantine_records import replay


def test_replay_dry_run():
    replay("orders", dry_run=True)
