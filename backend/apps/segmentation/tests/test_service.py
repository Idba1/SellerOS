from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from django.test import SimpleTestCase

from apps.segmentation.features import CustomerBehaviorFeatures
from apps.segmentation.service import (
    CustomerSegment,
    CustomerSegmentError,
    assign_customer_segment,
)


class CustomerSegmentAssignmentTests(SimpleTestCase):
    def features(self, *, purchase_count, recency_days, trailing_spend):
        return CustomerBehaviorFeatures(
            customer_id=UUID("00000000-0000-0000-0000-000000000001"),
            as_of=datetime(2026, 7, 1, tzinfo=timezone.utc),
            store_timezone="Asia/Dhaka",
            segment_rule_version="segment-v1",
            recorded_purchase_count=purchase_count,
            last_recorded_purchase_at=(
                None
                if purchase_count == 0
                else datetime(2026, 6, 1, tzinfo=timezone.utc)
            ),
            recency_days=recency_days,
            trailing_365_day_spend_bdt=Decimal(trailing_spend),
        )

    def test_boundaries_and_overlapping_rules_follow_documented_precedence(self):
        cases = (
            (0, None, "0.00", CustomerSegment.NO_RECORDED_ELIGIBLE_PURCHASE),
            (1, 30, "500.00", CustomerSegment.NEW),
            (1, 31, "500.00", CustomerSegment.ACTIVE_ONE_TIME),
            (2, 90, "9999.99", CustomerSegment.REPEAT),
            (2, 90, "10000.00", CustomerSegment.HIGH_VALUE),
            (3, 91, "12000.00", CustomerSegment.INACTIVE),
        )

        for count, recency, spend, expected in cases:
            with self.subTest(count=count, recency=recency, spend=spend):
                assignment = assign_customer_segment(
                    self.features(
                        purchase_count=count,
                        recency_days=recency,
                        trailing_spend=spend,
                    )
                )
                self.assertEqual(assignment.segment, expected)
                self.assertEqual(assignment.rule_version, "segment-v1")
                self.assertTrue(assignment.explanation)

    def test_inconsistent_or_unknown_feature_basis_is_rejected(self):
        wrong_version = self.features(
            purchase_count=1,
            recency_days=1,
            trailing_spend="100.00",
        )
        wrong_version = wrong_version.__class__(
            **{**wrong_version.__dict__, "segment_rule_version": "segment-v0"}
        )
        with self.assertRaisesMessage(
            CustomerSegmentError, "Unsupported customer feature rule version."
        ):
            assign_customer_segment(wrong_version)

        inconsistent_empty = self.features(
            purchase_count=0,
            recency_days=0,
            trailing_spend="0.00",
        )
        with self.assertRaisesMessage(
            CustomerSegmentError, "Empty purchase history has inconsistent recency."
        ):
            assign_customer_segment(inconsistent_empty)
