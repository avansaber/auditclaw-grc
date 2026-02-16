"""Tests for V2 Access Review actions (add/list/update campaigns and items).

Test IDs: V2-T4.1 through V2-T4.11
"""

import sqlite3
import sys
import os

# Ensure the V2 directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import get_v2_connection, make_args
from actions_batch2 import (
    action_add_access_review,
    action_list_access_reviews,
    action_update_access_review,
    action_add_review_item,
    action_list_review_items,
    action_update_review_item,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_campaign(conn, title="Q1 Access Review", reviewer="alice@example.com",
                     due_date="2026-06-30"):
    """Shortcut: create a campaign and return the result dict."""
    args = make_args(title=title, reviewer=reviewer, due_date=due_date)
    result = action_add_access_review(conn, args)
    assert result["status"] == "created"
    return result


def _add_item(conn, campaign_id, user_name="jdoe", resource="AWS Console",
              current_access="admin"):
    """Shortcut: add a review item and return the result dict."""
    args = make_args(
        campaign_id=campaign_id,
        user_name=user_name,
        resource=resource,
        current_access=current_access,
    )
    result = action_add_review_item(conn, args)
    assert result["status"] == "created"
    return result


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestAccessReviews:
    """V2-T4.x: Access review campaign and item operations."""

    def test_add_access_review(self, v2_db):
        """V2-T4.1: Create campaign with title, reviewer, due-date."""
        conn = get_v2_connection(v2_db)
        args = make_args(
            title="Q1 2026 Access Review",
            reviewer="alice@example.com",
            due_date="2026-06-30",
        )
        result = action_add_access_review(conn, args)
        conn.close()

        assert result["status"] == "created"
        assert result["id"] > 0
        assert result["title"] == "Q1 2026 Access Review"

    def test_list_access_reviews(self, v2_db):
        """V2-T4.2: Returns all campaigns."""
        conn = get_v2_connection(v2_db)
        _create_campaign(conn, title="Campaign A")
        _create_campaign(conn, title="Campaign B")

        args = make_args()
        result = action_list_access_reviews(conn, args)
        conn.close()

        assert result["status"] == "ok"
        assert result["count"] == 2
        titles = [c["title"] for c in result["campaigns"]]
        assert "Campaign A" in titles
        assert "Campaign B" in titles

    def test_list_access_reviews_by_status(self, v2_db):
        """V2-T4.3: --status filter returns only matching campaigns."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn, title="Active Campaign")
        # Transition one campaign to 'active'
        action_update_access_review(
            conn, make_args(id=camp["id"], status="active")
        )
        _create_campaign(conn, title="Draft Campaign")

        result = action_list_access_reviews(conn, make_args(status="active"))
        conn.close()

        assert result["count"] == 1
        assert result["campaigns"][0]["title"] == "Active Campaign"

    def test_update_access_review_start(self, v2_db):
        """V2-T4.4: Setting status=active auto-sets start_date when null."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)

        result = action_update_access_review(
            conn, make_args(id=camp["id"], status="active")
        )

        assert result["status"] == "updated"

        # Verify start_date was auto-populated
        row = conn.execute(
            "SELECT start_date, status FROM access_review_campaigns WHERE id = ?",
            (camp["id"],),
        ).fetchone()
        conn.close()

        assert row["status"] == "active"
        assert row["start_date"] is not None

    def test_update_access_review_complete(self, v2_db):
        """V2-T4.5: Setting status=completed auto-sets completed_at."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)

        action_update_access_review(
            conn, make_args(id=camp["id"], status="completed")
        )

        row = conn.execute(
            "SELECT completed_at, status FROM access_review_campaigns WHERE id = ?",
            (camp["id"],),
        ).fetchone()
        conn.close()

        assert row["status"] == "completed"
        assert row["completed_at"] is not None

    def test_add_review_item(self, v2_db):
        """V2-T4.6: Item created and campaign total_items incremented."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)

        item = _add_item(conn, camp["id"], user_name="jdoe", resource="S3 Bucket")

        assert item["id"] > 0
        assert item["campaign_id"] == camp["id"]

        # Verify total_items on the campaign was incremented
        row = conn.execute(
            "SELECT total_items FROM access_review_campaigns WHERE id = ?",
            (camp["id"],),
        ).fetchone()
        conn.close()

        assert row["total_items"] == 1

    def test_list_review_items(self, v2_db):
        """V2-T4.7: Returns items for campaign."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)
        _add_item(conn, camp["id"], user_name="alice", resource="EC2")
        _add_item(conn, camp["id"], user_name="bob", resource="RDS")

        result = action_list_review_items(
            conn, make_args(campaign_id=camp["id"])
        )
        conn.close()

        assert result["status"] == "ok"
        assert result["count"] == 2

    def test_update_review_item_approved(self, v2_db):
        """V2-T4.8: decision=approved sets reviewed_at and increments approved_items."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)
        item = _add_item(conn, camp["id"])

        result = action_update_review_item(
            conn, make_args(id=item["id"], decision="approved", reviewer="alice")
        )

        assert result["status"] == "updated"
        assert result["decision"] == "approved"

        # Verify reviewed_at is set on the item
        item_row = conn.execute(
            "SELECT reviewed_at FROM access_review_items WHERE id = ?",
            (item["id"],),
        ).fetchone()
        assert item_row["reviewed_at"] is not None

        # Verify campaign counters
        camp_row = conn.execute(
            "SELECT reviewed_items, approved_items FROM access_review_campaigns WHERE id = ?",
            (camp["id"],),
        ).fetchone()
        conn.close()

        assert camp_row["reviewed_items"] == 1
        assert camp_row["approved_items"] == 1

    def test_update_review_item_revoked(self, v2_db):
        """V2-T4.9: decision=revoked increments revoked_items."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)
        item = _add_item(conn, camp["id"])

        action_update_review_item(
            conn, make_args(id=item["id"], decision="revoked", reviewer="alice")
        )

        camp_row = conn.execute(
            "SELECT revoked_items FROM access_review_campaigns WHERE id = ?",
            (camp["id"],),
        ).fetchone()
        conn.close()

        assert camp_row["revoked_items"] == 1

    def test_campaign_counters(self, v2_db):
        """V2-T4.10: Review all items; reviewed_items == total_items."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)

        items = []
        for user in ("alice", "bob", "carol"):
            items.append(_add_item(conn, camp["id"], user_name=user, resource="Dashboard"))

        # Approve all three
        for it in items:
            action_update_review_item(
                conn, make_args(id=it["id"], decision="approved", reviewer="mgr")
            )

        camp_row = conn.execute(
            "SELECT total_items, reviewed_items, approved_items "
            "FROM access_review_campaigns WHERE id = ?",
            (camp["id"],),
        ).fetchone()
        conn.close()

        assert camp_row["total_items"] == 3
        assert camp_row["reviewed_items"] == 3
        assert camp_row["approved_items"] == 3

    def test_list_review_items_by_decision(self, v2_db):
        """V2-T4.11: --decision filter works."""
        conn = get_v2_connection(v2_db)
        camp = _create_campaign(conn)
        item_a = _add_item(conn, camp["id"], user_name="alice", resource="S3")
        item_b = _add_item(conn, camp["id"], user_name="bob", resource="EC2")

        # Approve alice, revoke bob
        action_update_review_item(
            conn, make_args(id=item_a["id"], decision="approved", reviewer="mgr")
        )
        action_update_review_item(
            conn, make_args(id=item_b["id"], decision="revoked", reviewer="mgr")
        )

        approved = action_list_review_items(
            conn, make_args(campaign_id=camp["id"], decision="approved")
        )
        revoked = action_list_review_items(
            conn, make_args(campaign_id=camp["id"], decision="revoked")
        )
        conn.close()

        assert approved["count"] == 1
        assert approved["items"][0]["user_name"] == "alice"
        assert revoked["count"] == 1
        assert revoked["items"][0]["user_name"] == "bob"
