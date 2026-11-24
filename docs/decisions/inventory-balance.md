# INV-01 inventory balance and movement-ledger decision

INV-01 selects a **cached current balance plus immutable ledger** representation. `StockUnit.quantity_on_hand` is the seller-visible current whole-unit balance; `InventoryMovement` is the nonzero historical evidence for changes. A low-stock state is true only when a seller has configured `low_stock_threshold` and `quantity_on_hand <= low_stock_threshold`. A missing threshold means “not configured,” never an inferred reorder value.

## Unit mapping

- A standalone product has one `StockUnit` with no variant.
- A variant-based product has one `StockUnit` per variant and no null-variant default unit.
- Product/store/variant relationships must agree. A movement carries the same store as its stock unit and its creator must be that store's owner or active staff member.

## Consistency rule

The balance is not recomputed on every read and no model `save()` mutates it from a movement. A later inventory service must, in one PostgreSQL transaction, lock the stock unit, validate that the resulting balance is nonnegative, insert one valid movement, and update the cached balance. It must reject duplicate `(stock_unit, movement_type, operation_id)` effects. Until that service/API task exists, direct model fixtures may create consistent initial state for tests but are not a seller stock-adjustment workflow.

Opening balances are positive; confirmation deductions are negative; cancellation/return restorations are positive; manual adjustments are nonzero and require a reason. Restoration rows reference the original confirmation deduction once. Order-item links remain deferred because order models do not exist yet.

## Deferred rules

**[DECISION REQUIRED] D-08 / ERD-03:** SKU/variant attribute structure, product archive behavior, and long-term product-to-stock conversion lifecycle remain open. **[DECISION REQUIRED] ERD-04/ERD-05 and DR-05:** final adjustment vocabulary, quantity granularity, order-item linkage, operation/retry policy, and reversal behavior alongside later order workflows require their own service/API decision. INV-01 does not create inventory routes, mutation actions, order effects, or low-stock notifications.
