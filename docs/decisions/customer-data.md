# CUSTOMER-01 customer-data boundary

Customer profiles contain only the approved seller-entered fields: a required display name and optional phone/email contact values. Phone text is trimmed; email is trimmed and syntax-validated by Django's `EmailField`, with its domain normalized. Empty optional contact values are stored as `NULL`.

Every customer has one direct `Store` owner. The model intentionally has no global or same-store uniqueness rule for phone/email; duplicate-contact reconciliation is future work. It also contains no address, social-platform identifier, payment detail, sensitive attribute, inferred profile, segmentation label, communication history, consent record, or automated-contact behavior.

Customer removal/anonymization is not implemented. The `Store` foreign key is `PROTECT`; a future order/privacy workflow must decide deletion, anonymization, retention, and linked-order behavior. **[DECISION REQUIRED] D-08 / ERD-06:** approve that workflow before adding ordinary delete operations or a customer API.
