# Luxury Command Center v10

This release keeps the existing family data and chore rules while adding a new household-management layer.

## New areas

- **Family Planner:** 14-day view combining chores, homework, appointments, reminders, meals, errands, and family events.
- **Household HQ:** shared shopping/supply checklist with categories, quantities, priorities, completion state, and deletion controls.
- **Family Goals:** shared or assigned goals with targets, units, due dates, progress meters, completion state, and parent removal controls.
- **Rewards Salon:** parent-configured rewards, point-based redemption, parent fulfillment/denial, automatic deduction, and automatic refund on denial.
- **Focus Mode:** hides analytics-heavy dashboard sections and keeps the daily operational view front and center. The choice persists in the browser.
- **Luxury UI:** obsidian, champagne gold, emerald, bronze, and ivory styling across dashboard, navigation, forms, login, panels, charts, and new pages.
- **Quick Launch Dock:** direct access from the dashboard to planner, shopping, goals, rewards, and messages.
- **Backup coverage:** the new planner, shopping, goals, rewards, and redemption tables are included in full exports.
- **One-command launcher:** `./start_dashboard.sh` creates the virtual environment if needed, installs dependencies, and starts the server.

The new database tables are additive and do not replace or truncate the existing family database.
