# ORDER-02 submitted-order creation policy

The submitted-order serializer accepts only optional same-store `customer_id`, one or more product/optional variant quantities, nonnegative order discount, and optional nonnegative seller delivery cost. The server creates `PENDING` (seller-facing “New”) in BDT. Clients cannot set store, status, timestamps, item snapshots, unit cost, price, or discount allocation.

For each active same-store product (and active matching variant where required), the server copies the current product name, optional variant name, and selling price into the new order item. Unit-cost snapshot remains `NULL` until the later confirmation transition, as required by the approved rules. Product lines may repeat. The serializer rejects a discount larger than the server-calculated gross and allocates valid discount proportionally using `ROUND_HALF_UP`, placing any rounding remainder on the final line so allocations sum exactly to the order discount.

**[DECISION REQUIRED] DR-08:** the later lifecycle service must enforce/record the approved price-and-identity freeze transition and permitted edits. **[DECISION REQUIRED] DR-02–DR-07:** confirmation, stock effects, returns/refunds, and reporting dates remain outside ORDER-02. This is a serializer/data-persistence policy, not an order API or autonomous pricing action.
