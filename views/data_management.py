"""Page 8 - Data Management (database status, import, quality, backup, reset)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import data_import as di
from analytics.data_validation import IMPORTABLE_TABLES, TABLE_SPECS, data_quality_summary
from auth import authentication as auth
from components.data_loader import clear_caches
from components.kpi_cards import page_header
from database import db
from scripts.backup_database import backup_database
from scripts.reset_demo_data import reset_demo_data
from utils.formatting import fmt_number

TABLE_HELP = {
    "branches": "One row per branch. region: North/South/East/West/Central; branch_type: Metro/Urban/Semi-Urban/Rural.",
    "customers": "Synthetic customers. customer_name should be a synthetic label (e.g. 'Customer 000123').",
    "transactions": "amount must be > 0. Both customer_id and branch_id must already exist.",
    "loans": "loan_status: Pending/Approved/Rejected/Disbursed/Closed. repayment_status: Not Applicable/Current/Overdue/Defaulted/Repaid.",
    "branch_financials": "One row per branch per month. reporting_month YYYY-MM-01. All amounts in ₹, not negative.",
    "customer_feedback": "satisfaction_score must be a whole number from 1 to 5.",
}


def render(ds, manager) -> None:
    page_header("Data Management", "Check database health, import new data, back up, and reset the demo dataset.")
    is_admin = manager.role == "Administrator"
    if not is_admin:
        st.info("You can view database status. Importing, resetting and managing accounts require the "
                "**Administrator** role.")

    tabs = st.tabs(["Database status", "Import data", "Data quality", "Backup & reset", "Import history"]
                   + (["Manager accounts"] if is_admin else []))
    with tabs[0]:
        _status()
    with tabs[1]:
        if is_admin:
            _import(manager)
        else:
            st.warning("Administrator role required to import data.")
    with tabs[2]:
        with st.spinner("Running data quality checks…"):
            q = data_quality_summary()
        issues = int(q["Issues"].sum())
        (st.success if issues == 0 else st.warning)(
            f"{len(q)} checks run · {issues} issue(s) found.")
        st.dataframe(q, hide_index=True, height=520)
        st.caption("Checks: missing required values, duplicate IDs, invalid dates, broken references, "
                   "negative/invalid amounts, out-of-range scores. Nothing is auto-corrected.")
    with tabs[3]:
        _backup_reset(is_admin)
    with tabs[4]:
        hist = di.import_history()
        if hist.empty:
            st.info("No files imported yet.")
        else:
            st.dataframe(hist, hide_index=True)
    if is_admin:
        with tabs[5]:
            _accounts(manager)


def _status() -> None:
    path = db.get_db_path()
    size = path.stat().st_size / 1024 / 1024 if path.exists() else 0
    rep = db.integrity_report()
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Database file**  \n`{path}`")
    c2.markdown(f"**Size**  \n{size:.2f} MB")
    c3.markdown(f"**Integrity**  \n{'✅ ' if rep['integrity'] == 'ok' else '❌ '}{rep['integrity']} · "
                f"FK violations: {rep['foreign_key_violations']}")
    st.markdown(f"**Last data refresh:** {db.get_metadata('last_data_refresh', 'never')}")
    counts = db.table_counts()
    st.dataframe(pd.DataFrame({"Table": list(counts), "Records": [fmt_number(v) for v in counts.values()]}),
                 hide_index=True)
    if st.button("🔄 Refresh dashboard data", key="dm_refresh"):
        stamp = db.mark_data_refreshed()
        clear_caches()
        st.success(f"Dashboard caches cleared — all pages now read fresh data (refreshed {stamp}).")


def _import(manager) -> None:
    table = st.selectbox("Target table", IMPORTABLE_TABLES, key="dm_table")
    spec = TABLE_SPECS[table]
    with st.expander("Expected file format", expanded=False):
        st.markdown(f"**Required columns:** `{'`, `'.join(spec['required'])}`")
        if spec["optional"]:
            st.markdown(f"**Optional columns:** `{'`, `'.join(spec['optional'])}`")
        st.markdown(f"**Dates:** YYYY-MM-DD ({', '.join(spec['dates'])}). {TABLE_HELP[table]}")
        st.download_button("Download empty template (CSV)", di.template_dataframe(table).to_csv(index=False),
                           f"{table}_template.csv", "text/csv", key="dm_tpl")
        st.caption("Sample files to try are in the project folder `data/samples/`.")
    up = st.file_uploader("Upload CSV or Excel (.xlsx)", type=["csv", "xlsx"], key=f"dm_upload_{table}")
    if up is None:
        return
    content = up.getvalue()
    digest = di.file_hash(content)
    try:
        raw = di.read_upload(up.name, content)
    except di.ImportErrorMessage as exc:
        st.error(str(exc))
        return
    st.markdown(f"**Preview** — {len(raw):,} rows, {len(raw.columns)} columns")
    st.dataframe(raw.head(20), hide_index=True, height=260)

    cleaned, log, report = di.prepare(table, raw)
    with st.expander("Cleaning steps applied", expanded=False):
        for line in log:
            st.write("•", line)
    if report.missing_columns:
        st.error("Required column(s) missing: " + ", ".join(report.missing_columns)
                 + ". Check you selected the right target table.")
        return
    if report.unexpected_columns:
        st.warning("These columns are not part of the table and will be ignored: "
                   + ", ".join(report.unexpected_columns))
    st.markdown("**Validation summary**")
    st.dataframe(pd.DataFrame(report.summary().items(), columns=["Check", "Count"]), hide_index=True)
    if di.already_imported(table, digest):
        st.error("This exact file has already been imported into this table — duplicate import blocked.")
        return
    if report.issues:
        st.warning(f"{len(report.invalid_rows)} row(s) have problems (row numbers match the file, header = row 1):")
        st.dataframe(report.issues_df(), hide_index=True, height=240)
    if report.existing_rows:
        st.info(f"{len(report.existing_rows - report.invalid_rows)} record(s) already exist in the database and "
                "will be skipped (no duplicates are created).")
    allow_partial = False
    if report.invalid_rows:
        allow_partial = st.checkbox("Import only the valid rows and skip rows with errors", key="dm_partial")
    if st.button("Import into database", type="primary", key="dm_import",
                 disabled=bool(report.invalid_rows) and not allow_partial):
        result = di.import_data(table, cleaned, report, file_name=up.name, digest=digest,
                                imported_by=manager.username, allow_partial=allow_partial)
        if result.success:
            clear_caches()
            st.success(f"{result.message} Records skipped: {result.skipped_existing} already existed, "
                       f"{result.skipped_invalid} invalid. Dashboard refreshed.")
        else:
            st.error(result.message)


def _backup_reset(is_admin: bool) -> None:
    st.markdown("#### Database backup")
    st.write("Creates a consistent copy using SQLite's online backup API (safe while the app is running).")
    if st.button("Create backup", key="dm_backup"):
        path = backup_database()
        st.session_state["dm_backup_path"] = str(path)
        st.success(f"Database backup created: `{path.name}` (in the backups/ folder)")
    if st.session_state.get("dm_backup_path"):
        from pathlib import Path
        p = Path(st.session_state["dm_backup_path"])
        if p.exists():
            st.download_button("⬇️ Download backup file", p.read_bytes(), p.name, "application/x-sqlite3",
                               key="dm_backup_dl")
    st.divider()
    st.markdown("#### Reset demo data")
    if not is_admin:
        st.warning("Administrator role required.")
        return
    st.warning("This **replaces all** branch, customer, transaction, loan, financial and feedback records with the "
             "original synthetic demo data. Manager accounts are kept. A backup is created automatically first.")
    confirm = st.checkbox("I understand that current business data will be replaced", key="dm_reset_ack")
    typed = st.text_input("Type RESET to confirm", key="dm_reset_text")
    if st.button("Reset demo data", key="dm_reset", disabled=not (confirm and typed.strip() == "RESET")):
        with st.spinner("Backing up and reloading demo data…"):
            result = reset_demo_data()
        clear_caches()
        st.success(f"Demo data reloaded ({sum(result['inserted'].values()):,} records). "
                   f"Backup saved first: `{result['backup']}`")


def _accounts(manager) -> None:
    managers = auth.list_managers()
    st.dataframe(pd.DataFrame([{"ID": m.manager_id, "Username": m.username, "Name": m.manager_name,
                                "Role": m.role, "Branch": m.assigned_branch_id or "All",
                                "Active": "Yes" if m.is_active else "No", "Last login": m.last_login or "-"}
                               for m in managers]), hide_index=True)
    st.caption("Password hashes are never displayed.")
    with st.expander("Add a manager"):
        with st.form("dm_add_mgr", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name")
            username = c2.text_input("Username")
            role = c1.selectbox("Role", auth.VALID_ROLES, index=2)
            branch = c2.text_input("Assigned branch ID (Branch Managers only, e.g. BR001)")
            pw = st.text_input("Initial password", type="password")
            if st.form_submit_button("Create manager"):
                try:
                    bid = branch.strip().upper() or None
                    if bid and not db.fetch_one("SELECT 1 FROM branches WHERE branch_id = ?", [bid]):
                        raise ValueError(f"Branch {bid} does not exist.")
                    auth.create_manager(username, pw, name, role=role, assigned_branch_id=bid)
                    st.success(f"Manager '{username}' created.")
                except ValueError as exc:
                    st.error(str(exc))
    with st.expander("Activate / deactivate a manager"):
        others = [m.username for m in managers if m.username != manager.username]
        if not others:
            st.caption("No other managers.")
        else:
            who = st.selectbox("Manager", others, key="dm_toggle_user")
            current = next(m for m in managers if m.username == who)
            label = "Deactivate" if current.is_active else "Activate"
            if st.button(f"{label} '{who}'", key="dm_toggle_btn"):
                auth.set_active(who, not current.is_active)
                st.success(f"'{who}' is now {'inactive' if current.is_active else 'active'}.")
                st.rerun()
