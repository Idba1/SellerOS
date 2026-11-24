# PRODUCT-01 catalogue and variant representation

PRODUCT-01 implements the minimum representation already recorded in the DB-02 data dictionary:

- A `Product` is directly owned by one `Store` and holds the seller-facing name, optional free-text category, BDT selling price, optional known unit cost, active flag, and `has_variants` flag.
- A `ProductVariant` is an optional named row owned by one `Product`; it inherits store, price, cost, category, and currency through that product.
- Variant names are unique case-insensitively within their parent product. They are not globally unique.
- A variant may be created only for a product whose `has_variants` flag is true. A standalone product has no variant rows.
- There is no SKU, option-type/option-value table, independent variant price/cost, stock unit, inventory quantity, or variant/store direct foreign key in this task.

This supports the approved optional-variant model without creating a second catalogue authority or client-controlled store scope. Store isolation remains server-side API work: model ownership alone does not authorize a request.

PRODUCT-02 write serializers therefore accept neither `store_id` nor `product_id`. A future authorized product endpoint resolves the current store server-side before creating a product. A future variant endpoint resolves a same-store parent product server-side and supplies it as serializer context. Read representations expose the variant's parent identifier for relationship display, not as permission authority.

PRODUCT-04 adds same-store product creation and partial update only. `is_active=false` is the available deactivation action; no hard delete exists. A product with existing variant rows cannot be changed to `has_variants=false` through this API, because that would contradict the chosen standalone-versus-variant representation. This is an API consistency guard, not a decision about future stock/order-history conversion.

PRODUCT-05 records the current duplicate semantics as executable tests: product names are not unique, including within one authorized store, because the data dictionary explicitly has no product-name uniqueness constraint. `sku` is not an accepted product API field because no SKU model field or uniqueness scope exists. This is not a substitute SKU policy.

## Deferred rules

**[DECISION REQUIRED] D-08 / ERD-03:** SKU scope/uniqueness, variant attribute structure, product archive/delete policy beyond the current active flag, variant/stock-unit mapping, and whether/how a product can change `has_variants` after inventory or order history exists.

The current `PROTECT` links preserve future historical references, but PRODUCT-01 does not create stock, order, or archive workflows. Product/variant deactivation only records current eligibility state; enforcement for future order creation belongs to the order task.
