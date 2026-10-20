# Alerts and sentence submission access update

- Alerts page: **Mark All Read** submits a CSRF-protected POST to `/notifications/read-all`.
- Only notifications belonging to the logged-in account that are currently unread are updated.
- Managers can open uploaded homework documents from the Approvals tab and verify sentence counts.
- Approved uploaded homework still earns one point per verified sentence, credited only once by the normal approval flow.
- Children cannot use the Approvals workflow.
- Includes `tests/test_alerts_manager_access.py` regression coverage.

Run tests after installing requirements: `python -m unittest tests.test_alerts_manager_access -v`.
