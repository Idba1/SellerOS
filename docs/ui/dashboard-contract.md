# Dashboard layout and data contract

## Scope and period input

The authenticated SellerOS dashboard is a read-only store overview. It never accepts a store ID: every source resolves the owner/active-staff store server-side.

The dashboard filter is inclusive store-local `start_date` / `end_date` (`YYYY-MM-DD`). The dashboard composition layer converts those dates to the exact endpoint-specific form:

- profit summary receives the inclusive dates directly;
- base sales and product performance receive the matching timezone-aware half-open timestamps; and
- no widget silently applies a default date range.

## Wireframe

```text
+--------------------------------------------------------------+
| Dashboard                         [From date] [To date]     |
+----------------------+----------------------+---------------+
| Delivered net sales  | Delivered orders     | Estimated profit|
+----------------------+----------------------+---------------+
| Product sales rows (not a profit ranking)                   |
+--------------------------------------------------------------+
| Unavailable until a contract exists: daily chart, low stock |
+--------------------------------------------------------------+
```

## Widget contract

| Visual | Source / fields | Unit and period | Empty or incomplete state |
| --- | --- | --- | --- |
| Delivered net sales card | `GET /api/v1/analytics/sales-summary/`; `totals.delivered_net_sales_before_reversals` | BDT; original delivery events in the selected half-open period | Show BDT 0.00 only when the endpoint returns its documented zero base total; disclose coverage status. It is not retained sales or profit. |
| Delivered orders card | Sales summary `totals.delivered_order_count` | Count; selected delivery-event period | Show 0 only from the endpoint's explicit response; no estimate. |
| Estimated profit card | `GET /api/v1/profit/summary/`; `totals.estimated_operational_profit`, `completeness`, warnings | BDT; selected inclusive store-local dates | Show unavailable, status and warnings when cost inputs are missing; never render `null` as BDT 0.00. |
| Product sales table | `GET /api/v1/analytics/product-performance/`; product ID, delivered units, delivered gross sales | Count and BDT; selected delivery-event period | Show documented no-eligible-events state. It is descriptive sales data, not product profit, recommendation, or forecast. |
| Calculation-basis disclosure | Profit summary `calculation_basis` and `completeness.warnings` | Text, same selected period | Always visible beside/under profit value; identifies exclusions and estimate boundary. |
| Daily revenue chart | No approved endpoint | Not available | Render an explicit unavailable state. Do not derive a chart from aggregate totals or synthetic values in a live dashboard. |
| Low-stock attention count | `GET /api/v1/analytics/dashboard/`; existing `StockUnit.is_low_stock` values | Count; current stock, not period sales | Show only configured-threshold units. A missing threshold is not low stock. |

## Frontend response types

The dashboard needs these response concepts before rendering live data:

- `DashboardPeriod`: requested local dates, derived endpoint bounds, and store timezone.
- `DashboardSales`: delivered net sales, delivered order count, data completeness and return-adjustment labels from the sales summary.
- `DashboardProfit`: nullable estimated profit/margin, completeness status, warnings, and calculation basis from the profit summary.
- `DashboardProductSalesRow`: product ID, delivered units, delivered gross sales only.
- `DashboardUnavailableWidget`: title, reason, and no fabricated numeric value.

The types must preserve money as backend decimal strings; frontend rendering formats them only after validation. The dashboard must not invent retention-adjusted sales, profit allocation, daily data, forecasts, recommendations, or a low-stock threshold.

## Verification checklist

1. Every displayed number has an endpoint field, unit, date basis, and same-store source.
2. Profit always displays its warning/basis metadata.
3. Empty, loading, error and incomplete-cost states are visually distinct from zero.
4. Unsupported chart and inventory widgets remain unavailable until their APIs exist.
5. No client query adds a tenant selector or bypasses authentication.
