# Homework and Logout Maintenance Fixes

This maintenance release preserves the existing database schema and data.

## Fixed

- Logout no longer fails when a stale CSRF token is submitted.
- Homework approval, needs-redo, and excuse controls now have normal POST fallbacks in addition to HTMX.
- Homework review no longer accesses the chore-only `note` column.

## Added

- Daily homework recurrence.
- Assign-to-all-children option.
- Recurring assignments are materialized forward when created:
  - Daily: 30 occurrences
  - Weekly: 12 occurrences
  - Monthly: 6 occurrences

No database reset or schema migration is required.
