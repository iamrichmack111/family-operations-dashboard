# Changelog

<!-- JASMIN-FRUIT-STUDIO-2.1 -->

## [2026-10-21] — Fruit Studio 2.1 & Dashboard Improvements

### Added
- Fruit Studio 2.1 with richer fruit-inspired color palettes.
- Light and Dark appearance options for fruit themes.
- Dashboard Focus Mode with task and review views.
- Four-character login PIN reset support through the administrative reset procedure.
- Background dashboard hosting through systemd and Gunicorn.
- Local dashboard access on port 8013.

### Improved
- Increased color saturation in Light Mode.
- Improved navigation, dashboard card, and assignment text contrast.
- Improved dashboard readability across fruit themes.
- Improved Point Requests access and dashboard navigation.
- Updated family dashboard theme styling and appearance controls.

### Data and Recovery
- Supported restoration of historical point requests, messages, and activity records from existing backups.
- Preserved family point balances during recovery procedures.
- Kept application databases and account credentials outside Git.

### Deployment
- Development dashboard hosted at `192.168.1.114:8013`.
- Local hostname shortcut configured as `family.local:8013`.
- Dashboard configured to continue running after terminal closure.
- Tailscale gateway configuration kept separate from local dashboard access.

**Note:** Local hostname mappings, systemd services, and database
contents are machine-specific and are not deployed by a Git push.

## Version 2026.10.19 — Family Operations Dashboard Update


## Fruit Studio 2.0 and Dashboard Recovery
**Updated:** 2026-10-21

### 🍓 Fruit Palette Studio 2.0
- Expanded 50 fruit palettes with light and dark variants.
- Added fruit-inspired skin, flesh, and foliage colors.
- Improved rare-fruit color differentiation.
- Added persistent light/dark theme preferences.
- Extended fruit colors across dashboard components.

### 🎀 Modern Dashboard
- Added modern rounded cards and glass-style panels.
- Improved buttons, forms, navigation, and tables.
- Added interactive Focus Mode.
- Introduced Tasks First, Reviews, and Full Overview views.
- Improved responsive styling for smaller screens.

### ⭐ Points and Requests
- Fixed Point Requests blueprint registration.
- Restored access to the Points and Point Requests pages.
- Increased the Chore Trade offer limit to 5,000 points.
- Added support for viewing original point-request records.

### 📜 Historical Data Recovery
- Located historical family databases on the family computer.
- Recovered original point-request records from older versions.
- Added database-preserving recovery procedures for messages and activity logs.
- Preserved original request amounts, dates, and statuses during recovery.
- Kept point balances and transactions separate from request imports.
- Added duplicate checks and safety backups to recovery procedures.

### 🔒 Data Protection
- Kept family databases out of source-control commits.
- Preserved existing application logs and financial records.
- Maintained separate production and development environments.

---

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

