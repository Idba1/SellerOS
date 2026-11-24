from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from django.test import SimpleTestCase, TestCase

from apps.catalog.models import Product

from apps.forecast.pipeline import (
    DailyDemandPoint,
    DailyDemandSeries,
    HORIZON_DAYS,
    assess_eligibility,
    evaluate_chronologically,
    forecast_product_demand,
    build_daily_product_series,
)
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class ForecastPipelineTests(SimpleTestCase):
    def series(self, units, *, coverage_complete=True, duplicates=0, returns=0):
        start = date(2026, 1, 1)
        return DailyDemandSeries(
            store_id=UUID("00000000-0000-0000-0000-000000000001"),
            product_id=UUID("00000000-0000-0000-0000-000000000002"),
            start_date=start,
            end_date=start + timedelta(days=len(units) - 1),
            points=tuple(DailyDemandPoint(start + timedelta(days=index), unit) for index, unit in enumerate(units)),
            coverage_complete=coverage_complete,
            duplicate_delivery_order_count=duplicates,
            return_affected_order_count=returns,
        )

    def test_insufficient_history_has_no_estimate(self):
        result = forecast_product_demand(self.series([1] * 10, coverage_complete=False))
        self.assertEqual(result.state, "insufficient_history")
        self.assertEqual(result.estimates, ())
        self.assertIn("history_coverage_unknown", result.limitations)

    def test_complete_known_series_is_chronological_and_reproducible(self):
        units = [1 if index % 4 == 0 else 0 for index in range(70)]
        series = self.series(units)
        eligibility = assess_eligibility(series)
        evaluation = evaluate_chronologically(series)
        first = forecast_product_demand(series)
        second = forecast_product_demand(series)
        self.assertTrue(eligibility.eligible)
        self.assertGreaterEqual(evaluation.fold_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(first.state, "available")
        self.assertEqual(len(first.estimates), HORIZON_DAYS)
        self.assertTrue(all(value >= 0 for value in first.estimates))

    def test_duplicates_and_returns_block_forecast_even_with_many_days(self):
        units = [1 if index % 4 == 0 else 0 for index in range(70)]
        result = forecast_product_demand(self.series(units, duplicates=1, returns=1))
        self.assertEqual(result.state, "insufficient_history")
        self.assertIn("duplicate_delivery_evidence", result.limitations)
        self.assertIn("return_treatment_not_supported", result.limitations)


class DailyDemandDatasetTests(TestCase):
    def test_known_delivery_events_produce_ordered_product_day_units(self):
        graph = create_store_graph(FactoryContext(namespace="forecast-series"))
        product = Product.objects.create(store=graph.store, name="Forecast Series Product", selling_price=10, unit_cost=4)
        for day, quantity in ((date(2026, 1, 1), 2), (date(2026, 1, 3), 3)):
            occurred_at = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
            order = SalesOrder.objects.create(store=graph.store, status=SalesOrder.Status.DELIVERED, delivered_at=occurred_at)
            OrderItem.objects.create(order=order, product=product, product_name_snapshot=product.name, quantity=quantity, selling_price_snapshot=10, unit_cost_snapshot=4)
            event = OrderStatusEvent.objects.create(order=order, from_status=SalesOrder.Status.SHIPPED, to_status=SalesOrder.Status.DELIVERED, initiated_by=graph.owner)
            OrderStatusEvent.objects.filter(pk=event.pk).update(occurred_at=occurred_at)
        series = build_daily_product_series(store=graph.store, product=product, start_date=date(2026, 1, 1), end_date=date(2026, 1, 3), coverage_complete=True)
        self.assertEqual([point.units for point in series.points], [2, 0, 3])
