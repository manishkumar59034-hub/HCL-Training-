"""Page 7 - Report Export. Every export reflects the filters currently selected."""
from __future__ import annotations

import streamlit as st

from components.kpi_cards import page_header
from utils import exports
from views.common import no_data


def render(ds) -> None:
    page_header("Report Export", "Download the current filtered analysis as CSV or Excel for sharing and offline review.")
    if no_data(ds):
        return
    st.markdown("**Filters applied to every export:** " + " · ".join(ds.filters.describe()))

    report = st.selectbox("Choose a report", list(exports.REPORTS), key="ex_report")
    df = exports.REPORTS[report](ds)
    st.caption(f"{len(df):,} rows × {len(df.columns)} columns")
    st.dataframe(df.head(200), hide_index=True, height=360)
    if len(df) > 200:
        st.caption("Preview shows the first 200 rows; the download contains all rows.")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Download CSV", exports.csv_bytes(df), exports.safe_filename(report, "csv"),
                       "text/csv", key="ex_csv")
    c2.download_button("⬇️ Download Excel", exports.excel_bytes({report[:31]: df,
                                                                 "Filters": exports.filters_sheet(ds.filters)}),
                       exports.safe_filename(report, "xlsx"),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="ex_xlsx")

    st.divider()
    st.subheader("Complete report workbook")
    st.write("One Excel file with a sheet for every report above plus the filters used.")
    if st.button("Prepare complete workbook", key="ex_prepare"):
        with st.spinner("Building workbook…"):
            st.session_state["ex_full"] = (repr(ds.filters), exports.full_report(ds))
    prepared = st.session_state.get("ex_full")
    if prepared and prepared[0] == repr(ds.filters):  # never offer a workbook built for old filters
        st.download_button("⬇️ Download complete report (.xlsx)", prepared[1],
                           exports.safe_filename("Bank_Branch_Performance_Report", "xlsx"),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="ex_full_dl")
