from app.process.thread_policy import is_ack_only_followup


def test_ack_only_detection():
    assert is_ack_only_followup("Thanks!")
    assert is_ack_only_followup("תודה")
    assert not is_ack_only_followup("Please investigate checkout 500 error.")
