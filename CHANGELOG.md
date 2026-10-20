## Version 2026.10.19 — Family Operations Dashboard Update

### Added
- 50 fruit-inspired dashboard themes.
- Fruit-only Theme Studio with updated illustrations.
- Parent-controlled manager payroll system.
- Manager payroll budget allocation.
- Manager distribution of points to household members.
- Payroll transaction history and balance tracking.
- Automatic sentence counting for uploaded homework.
- Sentence verification with one point awarded per sentence.
- Manager approval access for sentence submissions.
- Mark All Read functionality for notifications.

### Improved
- Updated dashboard theme navigation.
- Removed unrelated themes from Theme Studio.
- Improved manager permissions and approval workflows.
- Allowed Jasmin to verify and approve her own sentences.
- Separated manager payroll funds from personal points.
- Improved household points accounting.
- Added safeguards against duplicate point restorations.

### Points and Household Accounting
- Restored Jasmin's balance to 120,289 points.
- Corrected Aria's target balance to 14,000 points.
- Applied a one-time 2,000-point deduction to Zara.
- Preserved existing transaction history.

### Security
- Parent-only payroll budget allocation.
- Manager-only payroll distribution.
- Payroll spending restricted to allocated budgets.
- Role-based approval permissions.
- Database backup before point adjustments.
- Private household data excluded from Git commits.

### Deployment
- Flask application hosted on Linux.
- Systemd service: family-dashboard-v2.
- Application port: 8012.
- Automatic service restart enabled.
- Service continues running after terminal closure.

---

# Changelog

## 2026-10-19 — Fruit Themes and Manager Payroll

### Added
- 50 fruit-inspired dashboard themes.
- Fruit-only Theme Studio selection.
- Manager payroll administration.
- Parent-controlled payroll budget allocation.
- Manager point distribution for household work.
- Payroll payment history and budget tracking.
- Automatic sentence counting for homework submissions.
- Sentence verification and approval workflow.
- Bulk Mark All Read functionality for alerts.

### Changed
- Removed unrelated theme selections.
- Updated fruit palette names and illustrations.
- Expanded manager sentence-verification permissions.
- Allowed managers to approve their own submissions.
- Separated manager payroll budgets from personal balances.
- Improved navigation for themes and payroll.

### Data and Security
- Added point restoration and adjustment utilities.
- Preserved the existing household point ledger.
- Added one-time adjustment safeguards.
- Kept private databases, backups, and uploads
  outside the release commit.

## v67.0.0 — Family Operations Command Center

- Restored the Grievances tab.
- Added private grievance submit/history interface.
- Restored the parent grievance inbox and response workflow.
- Added the new Command Center dashboard redesign.
- Added desktop command-rail navigation.
- Added mobile quick-navigation dock.
- Redesigned cards, tables, forms, status indicators, and parent tools.
- Jasmin balance target updated to 12,000 points.
- Aria balance target updated to 10,000 points.
- Zara balance remains unchanged.
- Family Operations remains on port 8010.
- Tailscale Serve deployment target remains 127.0.0.1:8010.
- Added v67 release/install scripts.
- Added GitHub Actions CI verification.

