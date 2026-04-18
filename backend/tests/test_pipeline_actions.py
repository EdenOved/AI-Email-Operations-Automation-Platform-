from types import SimpleNamespace

from app.process.service import resolve_hubspot_action, resolve_jira_action


def test_create_when_no_parent_targets():
    ctx = SimpleNamespace(is_reply_like=False, parent_hubspot_ticket_id=None, parent_jira_issue_key=None)
    assert resolve_hubspot_action(ctx) == ("create", None)
    assert resolve_jira_action(ctx) == ("create", None)


def test_comment_for_reply_with_parent():
    ctx = SimpleNamespace(is_reply_like=True, parent_hubspot_ticket_id="123", parent_jira_issue_key="DEMO-1")
    assert resolve_hubspot_action(ctx) == ("comment", "123")
    assert resolve_jira_action(ctx) == ("comment", "DEMO-1")


def test_update_for_non_reply_with_parent():
    ctx = SimpleNamespace(is_reply_like=False, parent_hubspot_ticket_id="123", parent_jira_issue_key="DEMO-1")
    assert resolve_hubspot_action(ctx) == ("update", "123")
    assert resolve_jira_action(ctx) == ("update", "DEMO-1")
