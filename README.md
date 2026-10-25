# Department Academic MIS Portal

A clean academic department portal with a GUI, weekly faculty reporting, automatic growth milestones, task assignment and monthly Word MIS exports. Faculty, department particulars, goals and updates start empty. No personal reports or database are included.

## Run locally

Requires Python 3.10 or later. No third-party Python packages are required.

```sh
python server.py --open-browser
```

On Windows, you can also double-click **Start Portal.bat**. Open http://127.0.0.1:8765 if your browser does not open automatically. Keep the running process open while using the portal.

## Set up your department

1. Enter School, Department, Programmes, Dean and HOD in Workspace settings.
2. Add faculty names, designations and academic responsibilities.
3. Create measurable growth goals with start and due dates. Each goal generates planning, execution and review milestones. Auto-assignment matches responsibilities and open workload.
4. Collect weekly faculty updates and enter them in the template-specific A2 and A4–A10 forms. Mark submissions complete after entering the data. A1 comes from settings, A3 from tasks and A11 from the monthly summary.
5. Enter month-to-date values using consistent indicator names. The latest entry per faculty, section and indicator is used for the month; overlapping weekly totals are not added. Give shared department indicators one reporting owner to avoid duplicate rows.
6. Review the monthly summary, generate or download the Word report, obtain certification and submit by the 5th.

## Monthly schedule

The preceding month's report generates on or after the **2nd of each month**. While running, the portal checks every minute. A missed monthly generation catches up on the next start after the 2nd. Missing data is explicitly marked; example achievements are not treated as actual departmental results.

For generation while the portal window is closed, optionally run **Enable Automatic Reports.ps1** in PowerShell. It registers a Windows task named **Department Academic MIS Daily Check** at **09:00 daily**. Your computer must be on and your user session available. This script is not run automatically when you clone or start the portal. Disable or remove the task through Windows Task Scheduler when no longer needed. Dates use Asia/Kolkata (UTC+05:30); Windows task time follows your computer's local timezone.

The original blank MIS template is `mis-template.docx`. A1–A11 structure, headings, table geometry, styles and package files are retained. Filled content can increase the page count. Review the exported Word document before signing and submission; page-by-page visual fidelity has not been verified in this environment.

## Data and access

This version is for one coordinator on one computer. It binds to localhost and has no shared faculty login or email delivery. Faculty updates are collected externally and entered by the coordinator. GitHub stores the application source; pushing this repository does not publish a multi-user website.

Runtime data is created in `data/portal.sqlite3`, and generated reports in `data/reports/`. Both are excluded from Git. For a complete backup, stop the portal and copy its data folder. The sidebar JSON download provides a records-only backup; restore/import is not implemented.

## Checks

```sh
python -m unittest test_portal -v
```

Checks cover assignment, milestone dates, duplicate prevention, month boundaries, latest-snapshot reporting, missing data and template package preservation. Test records use isolated temporary databases.
