# Store-level permission enforcement — AUTH-03

`core.permissions` is the single server-side source for the current authorized store. It resolves an owner to its owned store or an active staff member to its membership store; it never accepts `store_id`, `owner_id`, a role flag, or a frontend route as authority.

## Required usage for future store-owned APIs

1. Call `require_authorized_store(request.user)` before a detail lookup, mutation, count, filter, aggregation, or serialization. It raises the existing 404 `not_found` response when no authorized store exists.
2. For lists, begin with `scope_to_authorized_store(queryset, request.user)`, then apply only endpoint-allowlisted filters. Never filter first and add a store condition later.
3. Use `has_store_access(account, store)` only for an already server-resolved object relationship; never compare a client-supplied store ID to grant access.
4. Validate every related object against the resolved store inside the transaction. Foreign IDs must cause no data disclosure or side effect.

AUTH-03 applies these rules to the existing `GET /api/v1/stores/current/` profile route. That endpoint permits no query parameters, so a supplied `store_id` is a 400 `validation_error` rather than an ignored or foreign-store selector. It remains owner/active-staff read-only, and its create route derives ownership from the token.

Only Account, Store, and StoreMembership records exist today. Product, customer, inventory, order, expense, and analysis APIs must use these helpers when their approved model/API tasks introduce store-owned querysets.
