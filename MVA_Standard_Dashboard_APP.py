# MVA | Standard Dashboard | APP | MEMBER | TRIPS
from snowflake.snowpark.context import get_active_session
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import datetime
import plotly.express as px
 
st.set_page_config(
    page_title="My Dashboard",
    page_icon="🚀",
    layout="wide",
)

st.title("💰 MVA Dashboard")
is_tamg = st.toggle("Show TA Only View", value=False)  # Default: TAMG

selected_mode = "TA_ONLY" if is_tamg else "TAMG"
    
# Fetch available baseline periods with descriptions
available_baseline_query = """
    SELECT DISTINCT 
        BASE_PERIOD_DESCRIPTION, 
        VALIDITY_START_DATE, 
        VALIDITY_END_DATE,
        CASE 
            WHEN CURRENT_DATE() BETWEEN VALIDITY_START_DATE AND VALIDITY_END_DATE 
            THEN 1 ELSE 0 
        END AS IS_CURRENT_BASELINE
    FROM 
   --analytics.acies.MVA_LTV
   {mva_ltv}
    ORDER BY VALIDITY_START_DATE DESC;
"""
available_performance_cohort_query = """
SELECT DISTINCT COHORT_START_DATE 
FROM 
--analytics.acies.MVA_COHORT_PERFORMANCE
{cohort_performance}
--user_scratch.X_ACIES_MVA.MVA_COHORT_PERFORMANCE_LATEST;
"""

query_for_static_view_template = """
  SELECT 
        MVA_NAME,
        CASE 
            WHEN MVA_LOCALE = 'en-US' THEN 'US'
            ELSE MVA_LOCALE
        END AS MVA_LOCALE,
        MVA_DEVICE_GROUP,
        LTV_INCREMENTAL_12M,
        LTV_BASELINE_12M,
        LTV_HISTORICAL_12M
    FROM 
      --analytics.acies.MVA_LTV
      {mva_ltv}
    WHERE 
        (CASE 
          WHEN MVA_LOCALE = 'en-US' THEN 'US'
          ELSE MVA_LOCALE
        END
        ) IN ('GLOBAL', 'US', 'ROW')
        AND BASE_PERIOD_DESCRIPTION = '{selected_baseline_desc}'
    GROUP BY 
        MVA_LOCALE, 
        MVA_DEVICE_GROUP, 
        MVA_NAME, 
        LTV_HISTORICAL_12M, 
        LTV_BASELINE_12M, 
        LTV_INCREMENTAL_12M
    ORDER BY 
    MVA_NAME,
    CASE 
        WHEN MVA_LOCALE = 'GLOBAL' THEN 1
        WHEN MVA_LOCALE = 'US' THEN 2
        WHEN MVA_LOCALE = 'ROW' THEN 3
    END,
    CASE
        WHEN MVA_DEVICE_GROUP = 'all_devices' THEN 1
        WHEN MVA_DEVICE_GROUP = 'desktop_tablet_web' THEN 2
        WHEN MVA_DEVICE_GROUP = 'mobile_web' THEN 3
        WHEN MVA_DEVICE_GROUP = 'all_apps' THEN 4
        WHEN MVA_DEVICE_GROUP = 'native_android' THEN 5
        WHEN MVA_DEVICE_GROUP = 'native_ios' THEN 6
        ELSE 7  
    END,
    MVA_DEVICE_GROUP;
"""


query_for_detailed_view_template = """
  
SELECT 
            MVA_NAME,
            CASE 
                WHEN MVA_LOCALE = 'en-US' THEN 'US'
                ELSE MVA_LOCALE
            END AS MVA_LOCALE,
            MVA_DEVICE_GROUP,
            LTV_INCREMENTAL_12M,
            LTV_BASELINE_12M,
            LTV_HISTORICAL_12M
        FROM 
          --analytics.acies.MVA_LTV
          {mva_ltv}
        WHERE 
            BASE_PERIOD_DESCRIPTION = '{selected_baseline_desc}'
        GROUP BY 
           MVA_LOCALE, MVA_DEVICE_GROUP, MVA_NAME, LTV_HISTORICAL_12M, 
            LTV_BASELINE_12M, LTV_INCREMENTAL_12M
        ORDER BY 
            MVA_LOCALE, 
           CASE
        WHEN MVA_DEVICE_GROUP = 'ALL_DEVICES' THEN 1
        WHEN MVA_DEVICE_GROUP = 'desktop_tablet_web' THEN 2
        WHEN MVA_DEVICE_GROUP = 'mobile_web' THEN 3
        WHEN MVA_DEVICE_GROUP = 'ALL_APPS' THEN 4
        WHEN MVA_DEVICE_GROUP = 'native_android' THEN 5
        WHEN MVA_DEVICE_GROUP = 'native_ios' THEN 6
        ELSE 7  
    END,
    MVA_DEVICE_GROUP;
"""


query_for_performance_period_template = """

 SELECT 
        MVA_NAME,
        CASE 
            WHEN MVA_LOCALE = 'en-US' THEN 'US'
            ELSE MVA_LOCALE
        END AS MVA_LOCALE,
        MVA_DEVICE_GROUP,
        CASE WHEN OBSERVED_LTV_15D IS NOT NULL THEN OBSERVED_LTV_15D ELSE EXTRAPOLATED_LTV_15D END AS LTV_15D,
        CASE WHEN OBSERVED_LTV_15D IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_15D_BASIS,
        CASE WHEN OBSERVED_LTV_30D IS NOT NULL THEN OBSERVED_LTV_30D ELSE EXTRAPOLATED_LTV_30D END AS LTV_30D,
        CASE WHEN OBSERVED_LTV_30D IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_30D_BASIS,
        CASE WHEN OBSERVED_LTV_45D IS NOT NULL THEN OBSERVED_LTV_45D ELSE EXTRAPOLATED_LTV_45D END AS LTV_45D,
        CASE WHEN OBSERVED_LTV_45D IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_45D_BASIS,
        CASE WHEN OBSERVED_LTV_60D IS NOT NULL THEN OBSERVED_LTV_60D ELSE EXTRAPOLATED_LTV_60D END AS LTV_60D,
        CASE WHEN OBSERVED_LTV_60D IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_60D_BASIS,
        CASE WHEN OBSERVED_LTV_03M IS NOT NULL THEN OBSERVED_LTV_03M ELSE EXTRAPOLATED_LTV_03M END AS LTV_03M,
        CASE WHEN OBSERVED_LTV_03M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_03M_BASIS,
        CASE WHEN OBSERVED_LTV_04M IS NOT NULL THEN OBSERVED_LTV_04M ELSE EXTRAPOLATED_LTV_04M END AS LTV_04M,
        CASE WHEN OBSERVED_LTV_04M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_04M_BASIS,
        CASE WHEN OBSERVED_LTV_05M IS NOT NULL THEN OBSERVED_LTV_05M ELSE EXTRAPOLATED_LTV_05M END AS LTV_05M,
        CASE WHEN OBSERVED_LTV_05M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_05M_BASIS,
        CASE WHEN OBSERVED_LTV_06M IS NOT NULL THEN OBSERVED_LTV_06M ELSE EXTRAPOLATED_LTV_06M END AS LTV_06M,
        CASE WHEN OBSERVED_LTV_06M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_06M_BASIS,
        CASE WHEN OBSERVED_LTV_07M IS NOT NULL THEN OBSERVED_LTV_07M ELSE EXTRAPOLATED_LTV_07M END AS LTV_07M,
        CASE WHEN OBSERVED_LTV_07M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_07M_BASIS,
        CASE WHEN OBSERVED_LTV_08M IS NOT NULL THEN OBSERVED_LTV_08M ELSE EXTRAPOLATED_LTV_08M END AS LTV_08M,
        CASE WHEN OBSERVED_LTV_08M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_08M_BASIS,
        CASE WHEN OBSERVED_LTV_09M IS NOT NULL THEN OBSERVED_LTV_09M ELSE EXTRAPOLATED_LTV_09M END AS LTV_09M,
        CASE WHEN OBSERVED_LTV_09M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_09M_BASIS,
        CASE WHEN OBSERVED_LTV_10M IS NOT NULL THEN OBSERVED_LTV_10M ELSE EXTRAPOLATED_LTV_10M END AS LTV_10M,
        CASE WHEN OBSERVED_LTV_10M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_10M_BASIS,
        CASE WHEN OBSERVED_LTV_11M IS NOT NULL THEN OBSERVED_LTV_11M ELSE EXTRAPOLATED_LTV_11M END AS LTV_11M,
        CASE WHEN OBSERVED_LTV_11M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_11M_BASIS,
        CASE WHEN OBSERVED_LTV_12M IS NOT NULL THEN OBSERVED_LTV_12M ELSE EXTRAPOLATED_LTV_12M END AS LTV_12M,
        CASE WHEN OBSERVED_LTV_12M IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_12M_BASIS
    FROM 
       --analytics.acies.MVA_COHORT_PERFORMANCE
       {cohort_performance}
    WHERE 
        COHORT_START_DATE = '{cohort_start_date}'
        AND COHORT_END_DATE = '{cohort_end_date}'
    ORDER BY 
        MVA_LOCALE, 
        MVA_DEVICE_GROUP;
"""


query_for_baseline_period_template = """
    SELECT 
        MVA_NAME,
        CASE 
            WHEN MVA_LOCALE = 'en-US' THEN 'US'
            ELSE MVA_LOCALE
        END AS MVA_LOCALE,
        MVA_DEVICE_GROUP,
        CAST(LTV_BASELINE_15D AS FLOAT) AS LTV_BASELINE_15D,
        CAST(LTV_BASELINE_30D AS FLOAT) AS LTV_BASELINE_30D,
        CAST(LTV_BASELINE_45D AS FLOAT) AS LTV_BASELINE_45D,
        CAST(LTV_BASELINE_60D AS FLOAT) AS LTV_BASELINE_60D,
        CAST(LTV_BASELINE_03M AS FLOAT) AS LTV_BASELINE_03M,
        CAST(LTV_BASELINE_04M AS FLOAT) AS LTV_BASELINE_04M,
        CAST(LTV_BASELINE_05M AS FLOAT) AS LTV_BASELINE_05M,
        CAST(LTV_BASELINE_06M AS FLOAT) AS LTV_BASELINE_06M,
        CAST(LTV_BASELINE_07M AS FLOAT) AS LTV_BASELINE_07M,
        CAST(LTV_BASELINE_08M AS FLOAT) AS LTV_BASELINE_08M,
        CAST(LTV_BASELINE_09M AS FLOAT) AS LTV_BASELINE_09M,
        CAST(LTV_BASELINE_10M AS FLOAT) AS LTV_BASELINE_10M,
        CAST(LTV_BASELINE_11M AS FLOAT) AS LTV_BASELINE_11M,
        CAST(LTV_BASELINE_12M AS FLOAT) AS LTV_BASELINE_12M
    
    FROM 
       --analytics.acies.MVA_LTV
       {mva_ltv}

    WHERE 
        BASE_PERIOD_DESCRIPTION = '{selected_baseline_desc}'
"""


flow_query1 = """
select mva_name,
    mva_device_group,
     OBSERVED_LTV_CURRENT_YOY_CORRECTION ,
      OBSERVED_LTV_1Y_PRIOR_YOY_CORRECTION ,
      PERFORMANCE_PERIOD_CORRECTION
from 
--analytics.acies.mva_correction_share
{correction_share}
where  concat(monthname(to_date(BASE_PERIOD_START_DATE)), '_', monthname(to_date(BASE_PERIOD_END_DATE)),'_',year(to_date(BASE_PERIOD_START_DATE))) = '{selected_baseline_desc}'
order by 1,2;
"""

flow_query2 = """
select mva_name,
    mva_device_group,
     observed_ltv_base_period_12m ,
      observed_ltv_base_period_part_12m ,
      correction_period_seasonality_correction
from 
--analytics.acies.mva_correction_share
{correction_share}
where 
--current_date() between correction_period_start_date and correction_period_end_date
concat(monthname(to_date(BASE_PERIOD_START_DATE)), '_', monthname(to_date(BASE_PERIOD_END_DATE)),'_',year(to_date(BASE_PERIOD_START_DATE))) = '{selected_baseline_desc}'
order by 1,2;
"""

flow_query3 = """
select mva_name,
    mva_device_group,
     performance_period_correction ,
      correction_period_seasonality_correction,
      correction_period_ltv_correction_share 
from 
--analytics.acies.mva_correction_share
{correction_share}
where 
--current_date() between correction_period_start_date and correction_period_end_date
concat(monthname(to_date(BASE_PERIOD_START_DATE)), '_', monthname(to_date(BASE_PERIOD_END_DATE)),'_',year(to_date(BASE_PERIOD_START_DATE))) = '{selected_baseline_desc}'
order by 1,2;
"""
query_chart = """
select mva_name, mva_device_group, year(cohort_start_date) as year, month(cohort_start_date) as month, cohort_description, distinct_mva_count, distinct_users_count, OBSERVED_LTV_60D
from 
--analytics.acies.MVA_COHORT_PERFORMANCE
{cohort_performance}
where COHORT_START_DATE between '2023-01-01' and '2024-12-01'
and mva_locale='GLOBAL' 
and mva_device_group = 'all_devices'
and mva_name!='app_download'

union all

select mva_name, mva_device_group,  year(cohort_start_date) as year, month(cohort_start_date) as month, cohort_description, distinct_mva_count, distinct_users_count, OBSERVED_LTV_60D
from 
--analytics.acies.MVA_COHORT_PERFORMANCE
{cohort_performance}
where COHORT_START_DATE between '2023-01-01' and '2024-12-01'
and mva_locale='GLOBAL' 
and mva_device_group in ('all_devices','native_ios','native_android')
and mva_name='app_download'
order by year, month
;
"""

def fetch_data_from_snowflake(query):
    session = get_active_session()  # Retrieve the active Snowflake session
    df = session.sql(query).to_pandas()  # Fetch the query results as a Pandas DataFrame
    return df

# Render the table with colored headers, split into three tables
def render_table_with_colors(df, selected_mva_type):
    html_tables = ""

    # Define columns for each table
    table_1_columns = ['LTV_INCREMENTAL_12M']
    table_2_columns = ['LTV_BASELINE_12M']
    table_3_columns = ['LTV_HISTORICAL_12M']

    # Helper function to generate table for a specific column set
    def generate_table(columns_to_pivot, table_name, ltv_column):
        # Start with caption before the table
        html_table = f"""<div style="overflow-x: auto; width: 100%; margin-bottom: 20px;">
                        <p><strong>{table_name} Table</strong></p>
                        <table border="1" style="border-collapse: collapse; width: 100%;">"""

        # Set color for the LTV column row
        if ltv_column == 'LTV_INCREMENTAL_12M':
            ltv_row_color = "#ffebe6"
        elif ltv_column == 'LTV_BASELINE_12M':
            ltv_row_color = "#d1e2f4"
        elif ltv_column == 'LTV_HISTORICAL_12M':
            ltv_row_color = "#abf5d1"
        else:
            ltv_row_color = "white"  # Default color if none of the above

        # Add table headers: LTV Column first, then MVA_NAME, MVA_LOCALE, and Device Groups
        html_table += "<tr>"
        num_device_columns = len(df['MVA_DEVICE_GROUP'].unique().tolist())
        colspan_value = num_device_columns + 2  # MVA_NAME and MVA_LOCALE + device groups
        for col in columns_to_pivot:
         formatted_col = col.replace("_", " ")  # Replace underscores with spaces
         html_table += f'<th style="background-color: {ltv_row_color}; padding: 5px; text-align: center;" colspan="{colspan_value}">{formatted_col}</th>'
         html_table += "</tr>"


        # Second row: MVA_NAME, MVA_LOCALE, and MVA_DEVICE_GROUP
        html_table += "<tr>"
        html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">MVA NAME</th>'
        html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">MVA LOCALE</th>'

        # Add MVA_DEVICE_GROUP columns
        unique_device_types = df['MVA_DEVICE_GROUP'].unique().tolist()
        unique_device_types = [x if x is not None else 'None' for x in unique_device_types]

       #for device_type in unique_device_types:
       #    html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">{device_type}</th>'
       #html_table += "</tr>"
        device_type_mapping = {
        "ALL_DEVICES": "ALL DEVICES",
        "desktop_tablet_web": "DESKTOP",
        "mobile_web": "MOBILE WEB",
        "ALL_APPS": "ALL APPS",
        "native_android": "NATIVE ANDROID",
        "native_ios": "NATIVE IOS",
        }

        # Add MVA_DEVICE_GROUP columns with formatted values
        for device_type in unique_device_types:
          formatted_device_type = device_type_mapping.get(device_type, device_type.replace("_", " ").title())
          html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">{formatted_device_type}</th>'
        html_table += "</tr>"

        # Third row: Values
        unique_mva_locale = df['MVA_LOCALE'].unique().tolist()
        unique_mva_locale = [x if x is not None else 'None' for x in unique_mva_locale]

        # Add table rows
        for mva_locale in unique_mva_locale:
            html_table += "<tr>"
            mva_locale_rows = df[df['MVA_LOCALE'] == mva_locale]

            # Add MVA_NAME and MVA_LOCALE as the first two columns
            html_table += f'<td style="padding: 5px; text-align: center;">{mva_locale_rows.iloc[-1]["MVA_NAME"].replace("_", " ")}</td>'
            html_table += f'<td style="padding: 5px; text-align: center;">{mva_locale_rows.iloc[-1]["MVA_LOCALE"]}</td>'

            # Add MVA_DEVICE_GROUP values
            for device_type in unique_device_types:
                if device_type == "None":
                    mva_locale_rows_by_device_type = mva_locale_rows[mva_locale_rows['MVA_DEVICE_GROUP'].isna()]
                else:
                    mva_locale_rows_by_device_type = mva_locale_rows[mva_locale_rows['MVA_DEVICE_GROUP'] == device_type]

                # Get value for the column
                for pivot_column in columns_to_pivot:
                    value = mva_locale_rows_by_device_type.iloc[-1][pivot_column]

                    if value != "None" and pd.notna(value):  # pd.notna() checks for NaN as well
                        formatted_value = f"${round(float(value), 2):,.2f}"  # Round to 2 decimals and add dollar sign
                    else:
                        formatted_value = "N/A"  # or you can set it to "None" or "Not available"
                    html_table += f'<td style="padding: 5px; text-align: center;">{formatted_value}</td>'

            html_table += "</tr>"

        html_table += "</table></div>"
        return html_table

    # Generate each table for Incremental, Baseline, and Historical with their respective colors
    html_tables += generate_table(table_1_columns, "Incremental", "LTV_INCREMENTAL_12M")  # Table 1: LTV_INCREMENTAL_12M
    html_tables += generate_table(table_2_columns, "Baseline", "LTV_BASELINE_12M")  # Table 2: LTV_BASELINE_12M
    # html_tables += generate_table(table_3_columns, "Historical", "LTV_HISTORICAL_12M")  # Table 3: LTV_HISTORICAL_12M

    return html_tables


# Render the table with colored headers, split into three tables
def render_table_with_colors_historical(df, selected_mva_type):
    html_tables = ""

    # Define columns for each table
    table_3_columns = ['LTV_HISTORICAL_12M']

    # Helper function to generate table for a specific column set
    def generate_table(columns_to_pivot, table_name, ltv_column):
        # Start with caption before the table
        html_table = f"""<div style="overflow-x: auto; width: 100%; margin-bottom: 20px;">
                        <p><strong>{table_name} Table</strong></p>
                        <table border="1" style="border-collapse: collapse; width: 100%;">"""

        # Set color for the LTV column row
        if ltv_column == 'LTV_HISTORICAL_12M':
            ltv_row_color = "#abf5d1"
        else:
            ltv_row_color = "white"  # Default color if none of the above

        # Add table headers: LTV Column first, then MVA_NAME, MVA_LOCALE, and Device Groups
        html_table += "<tr>"
        num_device_columns = len(df['MVA_DEVICE_GROUP'].unique().tolist())
        colspan_value = num_device_columns + 2  # MVA_NAME and MVA_LOCALE + device groups
        for col in columns_to_pivot:
         formatted_col = col.replace("_", " ")  # Replace underscores with spaces
         html_table += f'<th style="background-color: {ltv_row_color}; padding: 5px; text-align: center;" colspan="{colspan_value}">{formatted_col}</th>'
         html_table += "</tr>"


        # Second row: MVA_NAME, MVA_LOCALE, and MVA_DEVICE_GROUP
        html_table += "<tr>"
        html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">MVA NAME</th>'
        html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">MVA LOCALE</th>'

        # Add MVA_DEVICE_GROUP columns
        unique_device_types = df['MVA_DEVICE_GROUP'].unique().tolist()
        unique_device_types = [x if x is not None else 'None' for x in unique_device_types]

       #for device_type in unique_device_types:
       #    html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">{device_type}</th>'
       #html_table += "</tr>"
        device_type_mapping = {
        "ALL_DEVICES": "ALL DEVICES",
        "desktop_tablet_web": "DESKTOP",
        "mobile_web": "MOBILE WEB",
        "ALL_APPS": "ALL APPS",
        "native_android": "NATIVE ANDROID",
        "native_ios": "NATIVE IOS",
        }

        # Add MVA_DEVICE_GROUP columns with formatted values
        for device_type in unique_device_types:
          formatted_device_type = device_type_mapping.get(device_type, device_type.replace("_", " ").title())
          html_table += f'<th style="background-color: #f0f0f0; padding: 5px; text-align: center;">{formatted_device_type}</th>'
        html_table += "</tr>"

        # Third row: Values
        unique_mva_locale = df['MVA_LOCALE'].unique().tolist()
        unique_mva_locale = [x if x is not None else 'None' for x in unique_mva_locale]

        # Add table rows
        for mva_locale in unique_mva_locale:
            html_table += "<tr>"
            mva_locale_rows = df[df['MVA_LOCALE'] == mva_locale]

            # Add MVA_NAME and MVA_LOCALE as the first two columns
            html_table += f'<td style="padding: 5px; text-align: center;">{mva_locale_rows.iloc[-1]["MVA_NAME"].replace("_", " ")}</td>'
            html_table += f'<td style="padding: 5px; text-align: center;">{mva_locale_rows.iloc[-1]["MVA_LOCALE"]}</td>'

            # Add MVA_DEVICE_GROUP values
            for device_type in unique_device_types:
                if device_type == "None":
                    mva_locale_rows_by_device_type = mva_locale_rows[mva_locale_rows['MVA_DEVICE_GROUP'].isna()]
                else:
                    mva_locale_rows_by_device_type = mva_locale_rows[mva_locale_rows['MVA_DEVICE_GROUP'] == device_type]

                # Get value for the column
                for pivot_column in columns_to_pivot:
                    value = mva_locale_rows_by_device_type.iloc[-1][pivot_column]

                    if value != "None" and pd.notna(value):  # pd.notna() checks for NaN as well
                        formatted_value = f"${round(float(value), 2):,.2f}"  # Round to 2 decimals and add dollar sign
                    else:
                        formatted_value = "N/A"  # or you can set it to "None" or "Not available"
                    html_table += f'<td style="padding: 5px; text-align: center;">{formatted_value}</td>'

            html_table += "</tr>"

        html_table += "</table></div>"
        return html_table

    # Generate each table for Incremental, Baseline, and Historical with their respective colors
    #html_tables += generate_table(table_1_columns, "Incremental", "LTV_INCREMENTAL_12M")  # Table 1: LTV_INCREMENTAL_12M
    #html_tables += generate_table(table_2_columns, "Baseline", "LTV_BASELINE_12M")  # Table 2: LTV_BASELINE_12M
    html_tables += generate_table(table_3_columns, "Historical", "LTV_HISTORICAL_12M")  # Table 3: LTV_HISTORICAL_12M

    return html_tables



# Helper function to format numbers
def format_number(value):
    if value > 999_999_999:
        return f"{value / 1_000_000_000:.2f}b"
    elif value > 999_999:
        return f"{value / 1_000_000:.2f}m"
    else:
        return f"{value / 1_000:.2f}k"
  
mode_test = False

if mode_test:
    conn = st.connection("snowflake")
else:
    conn = get_active_session()

def create_multi_select_for_mva_selection_and_return_selected_options(df):
    mvaLocaleUnique =  df['MVA_LOCALE'].unique().tolist()
    options = st.multiselect(
            "Select the locales",
            mvaLocaleUnique,
            [],
        )
    return options
# Function to retrieve App Download data from Snowflake
def get_bounty_data(query_to_execute):
    # Replace with actual logic to fetch data
    df = conn.sql(query_to_execute).to_pandas()
    return df

def create_tabs():
    tab_standardview,tab_detailed_view,tab_chart,tab_flow = st.tabs(
            [ "🗃 Standard View", "💻 Detailed View", "📈 Realization Chart ","🚀Flow"])
    return tab_standardview,tab_detailed_view,tab_chart,tab_flow

def create_tabs_only_baseline():
  tab_chart= st.tabs(
            [  "📈 Realization Chart "])
  return tab_chart

def show_df_in_table_formatted(df, selected_mva_type):
    # Display the styled table
    if not df.empty:
        styled_table = render_table_with_colors(df, selected_mva_type)
        st.markdown(styled_table, unsafe_allow_html=True)
    else:
        st.write("Please select locales to display.")
        
def show_baseline_histrical_df_in_table_formatted(df, selected_mva_type):
    # Display the styled table
    if not df.empty:
        styled_table = render_table_with_colors_historical(df, selected_mva_type)
        st.markdown(styled_table, unsafe_allow_html=True)
    else:
        st.write("Please select locales to display.")


 
def show_bounty_metrics(selected_mva_type):
    # Fetch available baseline periods
    table_map = {
        "TAMG": {
            "mva_ltv": "enterprise_data.ltv.vw_mva_ltv",
            "cohort_performance": "enterprise_data.ltv.vw_mva_cohort_performance",
            "correction_share": "enterprise_data.ltv.vw_mva_correction_share"
        },
        "TA_ONLY": {
            "mva_ltv": "enterprise_data.ltv.vw_mva_ltv_ta_only_revenue",
            "cohort_performance": "enterprise_data.ltv.vw_mva_cohort_performance_ta_only_revenue",
            "correction_share": "enterprise_data.ltv.vw_mva_correction_share_dynamic"
        }
    }
    
    # Use the selected mode to get the appropriate table names
    mva_ltv_table = table_map[selected_mode]["mva_ltv"]
    cohort_performance_table = table_map[selected_mode]["cohort_performance"]
    correction_share_table = table_map[selected_mode]["correction_share"]
    
    available_baseline_temp = available_baseline_query \
            .replace("{mva_ltv}", mva_ltv_table)

    available_baseline_df = fetch_data_from_snowflake(available_baseline_temp)
    
    # Convert date columns to datetime and extract only the date
    available_baseline_df["VALIDITY_START_DATE"] = pd.to_datetime(available_baseline_df["VALIDITY_START_DATE"]).dt.date
    available_baseline_df["VALIDITY_END_DATE"] = pd.to_datetime(available_baseline_df["VALIDITY_END_DATE"]).dt.date
    
    # Create a formatted baseline period label
    def format_baseline_period(row):
        return f"{row['VALIDITY_START_DATE'].strftime('%b')}-{row['VALIDITY_END_DATE'].strftime('%b %Y')}"
    
    # Add formatted labels to the dataframe
    available_baseline_df["VALIDITY_PERIOD_LABEL"] = available_baseline_df.apply(format_baseline_period, axis=1)
    
    # Get the label for the current baseline (if any)
    current_baseline_label = (
        available_baseline_df.loc[available_baseline_df["IS_CURRENT_BASELINE"] == 1, "VALIDITY_PERIOD_LABEL"]
        .dropna()
        .iloc[0]  # pick the first one if multiple rows have IS_CURRENT_BASELINE = 1
        if (available_baseline_df["IS_CURRENT_BASELINE"] == 1).any()
        else None  # fallback if none found
    )
    
    
    # Get unique validity period labels for selection
    validity_period_labels = sorted(available_baseline_df["VALIDITY_PERIOD_LABEL"].unique())
    
    # Sidebar checkbox for baseline view mode
    only_view_baseline = st.sidebar.checkbox("Only view baseline", value=False)
    
    # Lists to hold queries for selected baselines
    query_list_for_static_view_only_baseline = []
    query_list_for_detailed_view_only_baseline = []
    selected_basedline_description_only_baseline = []
    
    if only_view_baseline:
        # Multiselect for baseline periods with default as current baseline (if present)
        selected_baselines = st.sidebar.multiselect(
            "Select validity periods",
            options=validity_period_labels,
            default=[current_baseline_label] if current_baseline_label else []
        )
    
        # Filter the dataframe based on selected labels
        df_filtered = available_baseline_df[available_baseline_df["VALIDITY_PERIOD_LABEL"].isin(selected_baselines)]
    
        if not df_filtered.empty:
            st.sidebar.info("You have selected the following baseline period(s):")
    
            for idx, row in df_filtered.iterrows():
                baseline_desc = row["BASE_PERIOD_DESCRIPTION"]
                st.sidebar.markdown(f"- {baseline_desc}")
                selected_basedline_description_only_baseline.append(baseline_desc)
    
                # Store queries for each selected baseline
                s_query = query_for_static_view_template.format(selected_baseline_desc=baseline_desc, mva_ltv=mva_ltv_table)
                query_list_for_static_view_only_baseline.append(s_query)
    
                d_query = query_for_detailed_view_template.format(selected_baseline_desc=baseline_desc, mva_ltv=mva_ltv_table)
                query_list_for_detailed_view_only_baseline.append(d_query)
    
        else:
            st.sidebar.warning("No baseline periods selected.")
    
    else:
        # Sidebar dropdown to select a single baseline period
        selected_validity_label = st.sidebar.selectbox(
            "Select Validity Period",
            validity_period_labels,
            index=validity_period_labels.index(current_baseline_label) if current_baseline_label else 0
        )
    
        df_filtered = available_baseline_df[available_baseline_df["VALIDITY_PERIOD_LABEL"] == selected_validity_label]
    
        if not df_filtered.empty:
            selected_baseline_desc = df_filtered.iloc[0]["BASE_PERIOD_DESCRIPTION"]
            validity_start_date = df_filtered.iloc[0]["VALIDITY_START_DATE"]
            validity_end_date = df_filtered.iloc[0]["VALIDITY_END_DATE"]
            st.sidebar.info(f"**Selected Baseline Period:** {selected_baseline_desc}")

            # Generate cohort months from validity period
            cohort_months = pd.date_range(start=validity_start_date, end=validity_end_date, freq='MS').strftime('%b %Y').tolist()

            available_performance_cohort_temp = available_performance_cohort_query \
                .replace("{cohort_performance}", cohort_performance_table)
            available_performance_cohort = fetch_data_from_snowflake(available_performance_cohort_temp)
            cohort_start_date = available_performance_cohort["COHORT_START_DATE"].dropna().tolist()
            formatted_cohort_start_date = [date.strftime('%b %Y') for date in cohort_start_date]
    
            common_date = list(set(cohort_months) & set(formatted_cohort_start_date))
            
            # Format the data queries using the selected baseline and cohort description
            query_for_static_view = query_for_static_view_template.format(selected_baseline_desc=selected_baseline_desc,mva_ltv=mva_ltv_table)
            query_for_detailed_view = query_for_detailed_view_template.format(selected_baseline_desc=selected_baseline_desc, mva_ltv=mva_ltv_table)
            
            
        else:
            st.sidebar.warning("No baseline period available for the selected description.")


    if not only_view_baseline:   
            # Create Tabs
            tab_standardview, tab_detailed_view, tab_chart, tab_flow = create_tabs()
        
             
            with tab_standardview:
                if only_view_baseline:
                    if(len(query_list_for_static_view_only_baseline) > 0):
                        for s_query in query_list_for_static_view_only_baseline:
                          df = fetch_data_from_snowflake(s_query)
                          filtered_df_on_selected_mva_type = df[df['MVA_NAME'].isin([selected_mva_type])]
                          show_df_in_table_formatted(filtered_df_on_selected_mva_type, selected_mva_type)
                    else:
                        st.write("No data available for selected baseline")
                        
                else:
                    st.title("MVA Metrics Table")
                    df = fetch_data_from_snowflake(query_for_static_view)
                    filtered_df_on_selected_mva_type = df[df['MVA_NAME'].isin([selected_mva_type])]
                    show_df_in_table_formatted(filtered_df_on_selected_mva_type, selected_mva_type)
                    
            with tab_detailed_view:
                if only_view_baseline:
                    if(len(query_list_for_detailed_view_only_baseline) > 0):
                        for d_query in query_list_for_detailed_view_only_baseline:
                            df = fetch_data_from_snowflake(d_query)
                            filtered_df_on_selected_mva_type = df[df['MVA_NAME'].isin([selected_mva_type])]
                            options = create_multi_select_for_mva_selection_and_return_selected_options(filtered_df_on_selected_mva_type)
                            
                            filtered_df = filtered_df_on_selected_mva_type[filtered_df_on_selected_mva_type['MVA_LOCALE'].isin(options)]
                            # st.write(filtered_df)
                            show_df_in_table_formatted(filtered_df, selected_mva_type)
                    
                else:
                    df = fetch_data_from_snowflake(query_for_detailed_view)
                    filtered_df_on_selected_mva_type = df[df['MVA_NAME'].isin([selected_mva_type])]
                    options = create_multi_select_for_mva_selection_and_return_selected_options(filtered_df_on_selected_mva_type)
                    
                    filtered_df = filtered_df_on_selected_mva_type[filtered_df_on_selected_mva_type['MVA_LOCALE'].isin(options)]
                    # st.write(filtered_df)
                    show_df_in_table_formatted(filtered_df, selected_mva_type)
              
            with tab_chart:
           
                    # Fetch the baseline data
                    query_for_baseline_period = query_for_baseline_period_template.format(selected_baseline_desc=selected_baseline_desc,mva_ltv=mva_ltv_table)
                    baseline_df = fetch_data_from_snowflake(query_for_baseline_period)
                    baseline_cohort_df = baseline_df[baseline_df['MVA_NAME'].isin([selected_mva_type])]
                    
                    # Dropdown for MVA_LOCALE selection
                    mva_locale_values = baseline_cohort_df['MVA_LOCALE'].unique()
                    top_options = ['GLOBAL', 'US', 'ROW']
                    remaining_options = [locale for locale in mva_locale_values if locale not in top_options]
                    ordered_mva_locale_values = top_options + remaining_options
                    
                    # Create columns for dropdowns
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                      
                        selected_cohort = st.multiselect(
                            "Select the Cohort of Performance",
                            options=common_date,  # List of available cohort dates
                            default=[common_date[0]] if common_date else []  # Select the first one by default if available
                        )
            
                   
                    
                    with col2:
                        selected_mva_locale = st.selectbox(
                            "Select MVA Locale",
                            ordered_mva_locale_values,
                            index=ordered_mva_locale_values.index('GLOBAL') if 'GLOBAL' in ordered_mva_locale_values else 0
                        )
                    
                    with col3:
                        selected_mva_device_group = st.selectbox(
                            "Select MVA Device Group",
                            options=baseline_cohort_df['MVA_DEVICE_GROUP'].unique(),
                            index=list(baseline_cohort_df['MVA_DEVICE_GROUP'].unique()).index('all_devices')
                            if 'all_devices' in baseline_cohort_df['MVA_DEVICE_GROUP'].unique() else 0
                        )
                    
                    # Convert selected cohorts into a date range for filtering
                    if selected_cohort:
                        cohort_start_dates = [pd.to_datetime(cohort).replace(day=1).date() for cohort in selected_cohort]
                        cohort_end_dates = [(pd.to_datetime(cohort) + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date() for cohort in selected_cohort]
                    else:
                        cohort_start_dates = []
                        cohort_end_dates = []
                   
                    # Fetch performance data for all selected cohorts
                    
            
                    query_for_performance_period = []
                    df = []
                    filtered_df= []
                    performance_cohort_df = []
                    for start_date, end_date in zip(cohort_start_dates, cohort_end_dates):
                         query_for_performance_period.append(query_for_performance_period_template.format(
                            cohort_start_date=start_date,
                            cohort_end_date=end_date,
                            cohort_performance=cohort_performance_table
                        ))
                    
                    for each_query_for_performace_period in query_for_performance_period:
                        df.append(fetch_data_from_snowflake(each_query_for_performace_period))
                        filtered_df.append(df[len(df)-1][df[len(df)-1]['MVA_NAME'].isin([selected_mva_type])])
                        performance_cohort_df.append(pd.DataFrame()) # Initialize an empty DataFrame
            
                    # Append the filtered data to the main DataFrame
                    for index, each_filtered_df in enumerate(filtered_df):
                    #for each_filtered_df in filtered_df:
                        
                        performance_cohort_df[index] = pd.concat([performance_cohort_df[index], filtered_df[index]], ignore_index=True)
            
                    # Filter the baseline and performance cohort data
                    filtered_baseline_cohort_on_selected_mva_type = baseline_cohort_df[
                        (baseline_cohort_df['MVA_NAME'] == selected_mva_type) & 
                        (baseline_cohort_df['MVA_LOCALE'] == selected_mva_locale) &
                        (baseline_cohort_df['MVA_DEVICE_GROUP'] == selected_mva_device_group)
                    ]
                    filtered_performance_cohort_on_selected_mva_type = []
            
                    for each_performance_cohort_df in performance_cohort_df:
                        filtered_performance_cohort_on_selected_mva_type.append(each_performance_cohort_df[
                            (each_performance_cohort_df['MVA_NAME'] == selected_mva_type) & 
                            (each_performance_cohort_df['MVA_LOCALE'] == selected_mva_locale) &
                            (each_performance_cohort_df['MVA_DEVICE_GROUP'] == selected_mva_device_group)
                        ])
                    
                    if filtered_baseline_cohort_on_selected_mva_type.empty or len(filtered_performance_cohort_on_selected_mva_type) < 0:
                        st.warning(f"No data available for selected locale {selected_mva_locale} and device group {selected_mva_device_group}.")
                    else:
                        st.write("")
                        #for each_filtered_performance_cohort_on_selected_mva_type in filtered_performance_cohort_on_selected_mva_type:
                        #    st.dataframe(each_filtered_performance_cohort_on_selected_mva_type)
            
                    # Show the filtered data
                    # st.write(filtered_baseline_cohort_on_selected_mva_type)
            
                    # Display the filtered data
                    # st.write(filtered_baseline_cohort_on_selected_mva_type)
            
                    
                    st.text(f'The chart shows the LTV realization curve for {selected_baseline_desc} - Baseline Cohort')
                    
                    performance_period_columns_reference = [
                        'LTV_15D_BASIS', 'LTV_30D_BASIS', 'LTV_45D_BASIS', 'LTV_60D_BASIS',
                        'LTV_03M_BASIS', 'LTV_04M_BASIS', 'LTV_05M_BASIS', 'LTV_06M_BASIS',
                        'LTV_07M_BASIS', 'LTV_08M_BASIS', 'LTV_09M_BASIS', 'LTV_10M_BASIS',
                        'LTV_11M_BASIS', 'LTV_12M_BASIS'
                    ]
                    performance_period_columns = [
                        'LTV_15D', 'LTV_30D', 'LTV_45D', 'LTV_60D', 'LTV_03M', 'LTV_04M',
                        'LTV_05M', 'LTV_06M', 'LTV_07M', 'LTV_08M', 'LTV_09M', 'LTV_10M',
                        'LTV_11M', 'LTV_12M'
                    ]
                    performance_period_labels = [
                        'LTV_15D', 'LTV_30D', 'LTV_45D', 'LTV_60D', 'LTV_3M', 'LTV_4M', 'LTV_5M', 'LTV_6M',
                        'LTV_7M', 'LTV_8M', 'LTV_9M', 'LTV_10M', 'LTV_11M', 'LTV_12M'
                    ]
                    
                    # Map each label to a datetime value (arbitrary starting point)
                    start_date = datetime.datetime(2023, 1, 1)
                    date_mapping = {
                        'LTV_15D': start_date + datetime.timedelta(days=15),
                        'LTV_30D': start_date + datetime.timedelta(days=30),
                        'LTV_45D': start_date + datetime.timedelta(days=45),
                        'LTV_60D': start_date + datetime.timedelta(days=60),
                        'LTV_3M': start_date + datetime.timedelta(days=90),
                        'LTV_4M': start_date + datetime.timedelta(days=120),
                        'LTV_5M': start_date + datetime.timedelta(days=150),
                        'LTV_6M': start_date + datetime.timedelta(days=180),
                        'LTV_7M': start_date + datetime.timedelta(days=210),
                        'LTV_8M': start_date + datetime.timedelta(days=240),
                        'LTV_9M': start_date + datetime.timedelta(days=270),
                        'LTV_10M': start_date + datetime.timedelta(days=300),
                        'LTV_11M': start_date + datetime.timedelta(days=330),
                        'LTV_12M': start_date + datetime.timedelta(days=360),
                    }
                
                    performance_period_actuals = []
                    performance_period_extrapolated = []
            
                    fig = go.Figure()
                    if filtered_baseline_cohort_on_selected_mva_type.empty or len(filtered_performance_cohort_on_selected_mva_type) < 0:
                        st.warning(f"No data available for selected locale ({selected_mva_locale}) and device group ({selected_mva_device_group}).")
                    else: 
                     for index_inside, each_cohort_selected_mva_type in enumerate(filtered_performance_cohort_on_selected_mva_type):
                         performance_period_actuals.append([])
                         performance_period_extrapolated.append([])
                         

                    ltv_12m_values = [
                        df['LTV_12M'].iloc[-1] if 'LTV_12M' in df.columns else None
                        for df in filtered_performance_cohort_on_selected_mva_type
                    ]

                    colors = ['red', 'green', 'purple']
                
                    for index, performance_period_column_reference in enumerate(performance_period_columns_reference):
                        for index_inside, each_cohort_selected_mva_type in enumerate(filtered_performance_cohort_on_selected_mva_type):
                            isActual = each_cohort_selected_mva_type[performance_period_column_reference].iloc[-1] == 'OBSERVED'
                            performance_period_value = each_cohort_selected_mva_type[performance_period_columns[index]].iloc[-1]
                            period_date = date_mapping[performance_period_labels[index]]
                            period_label = cohort_start_dates[index_inside].strftime('%b %Y')
                            period_label_text = performance_period_labels[index]
                            
                            # Calculate realization % based on ltv_12m
                            ltv_12m = ltv_12m_values[index_inside]
                            if ltv_12m and ltv_12m != 0:
                                realization_pct = (performance_period_value / ltv_12m) * 100
                                hover_text = f"{period_label_text}:${performance_period_value:.2f} ({realization_pct:.2f}%)"
                            else:
                                hover_text = f"{period_label_text}:${performance_period_value:.2f} (N/A)"
                            
                            performance_period_label_value_pair = {
                                'date': period_date,
                                'value': performance_period_value,
                                'label': period_label,
                                'hover': hover_text
                            }
                            
                            # Append to actuals or extrapolated based on the data
                            (performance_period_actuals[index_inside] if isActual else performance_period_extrapolated[index_inside]).append(performance_period_label_value_pair)
                    
                    # === Process and plot actual values ===
                    for index, sublist in enumerate(performance_period_actuals):
                        if not sublist:
                            continue
                        actual_dates = [obj['date'] for obj in sublist]
                        actual_values = [obj['value'] for obj in sublist]
                        actual_labels = [obj['label'] for obj in sublist]
                        hover_texts = [obj['hover'] for obj in sublist]
                        
                        fig.add_trace(go.Scatter(
                            x=actual_dates,
                            y=actual_values,
                            mode='lines+markers+text',
                            name=f"{actual_labels[0]} Observed",
                            text=[f"${val:.2f}" for val in actual_values],
                            textposition="bottom center",
                            line=dict(color=colors[index]),
                            marker=dict(size=8),
                            hovertext=hover_texts,
                            hoverinfo='text'
                        ))
                    
                    # === Process and plot extrapolated values ===
                    for index, sublist in enumerate(performance_period_extrapolated):
                        if not sublist:
                            continue
                        extrapolated_dates = [obj['date'] for obj in sublist]
                        extrapolated_values = [obj['value'] for obj in sublist]
                        extrapolated_hovers = [obj['hover'] for obj in sublist]
                    
                        # Add last actual point for continuity
                        if performance_period_actuals[index]:
                            last_actual = performance_period_actuals[index][-1]
                            extrapolated_dates.insert(0, last_actual['date'])
                            extrapolated_values.insert(0, last_actual['value'])
                            extrapolated_hovers.insert(0, last_actual['hover'])
                    
                        label = performance_period_actuals[index][0]['label'] if performance_period_actuals[index] else sublist[0]['label']
                    
                        fig.add_trace(go.Scatter(
                            x=extrapolated_dates,
                            y=extrapolated_values,
                            mode='lines+markers+text',
                            name=f"{label} Extrapolated",
                            line=dict(dash='5px,10px', color=colors[index], width=2),
                            text=[f"${val:.2f}" for val in extrapolated_values],
                            textposition="bottom center",
                            marker=dict(size=8),
                            hovertext=extrapolated_hovers,
                            hoverinfo='text'
                        ))
            
                    # Process and plot baseline data
                    baseline_period_columns = [
                        'LTV_BASELINE_15D', 'LTV_BASELINE_30D', 'LTV_BASELINE_45D',
                        'LTV_BASELINE_60D', 'LTV_BASELINE_03M', 'LTV_BASELINE_04M',
                        'LTV_BASELINE_05M', 'LTV_BASELINE_06M', 'LTV_BASELINE_07M',
                        'LTV_BASELINE_08M', 'LTV_BASELINE_09M', 'LTV_BASELINE_10M',
                        'LTV_BASELINE_11M', 'LTV_BASELINE_12M'
                    ]
                    # Create a new dictionary to store the realization percentage columns
                    realization_columns = {}
            
                    # Iterate through the columns and calculate the realization percentages
                    for column in baseline_period_columns:  # Exclude the last column (LTV_BASELINE_12M)
                        ratio_column_name = f'{column}_to_LTV_BASELINE_12M'
                        
                        # Calculate the ratio and convert to percentage
                        filtered_baseline_cohort_on_selected_mva_type[ratio_column_name] = (
                            filtered_baseline_cohort_on_selected_mva_type[column] / filtered_baseline_cohort_on_selected_mva_type['LTV_BASELINE_12M']
                        ) * 100
                        
                        # Optionally, store in the dictionary for later use
                        realization_columns[ratio_column_name] = filtered_baseline_cohort_on_selected_mva_type[ratio_column_name]
                    
                    # Show the resulting DataFrame with new realization percentage columns
                    #st.write(filtered_baseline_cohort_on_selected_mva_type)
            
            
                    if filtered_baseline_cohort_on_selected_mva_type.empty:
                        st.warning(f"No baseline data available for {selected_mva_locale}, {selected_mva_device_group}.")
                    else:
                     baseline_values = [round(val, 2) for val in filtered_baseline_cohort_on_selected_mva_type[baseline_period_columns].iloc[0]]
                     baseline_dates = [date_mapping[label] for label in performance_period_labels]
            
                    
                    # Define the mapping between period labels and the corresponding column names in your dataset
                    realization_column_mapping = {
                        'LTV_15D': 'LTV_BASELINE_15D_to_LTV_BASELINE_12M',
                        'LTV_30D': 'LTV_BASELINE_30D_to_LTV_BASELINE_12M',
                        'LTV_45D': 'LTV_BASELINE_45D_to_LTV_BASELINE_12M',
                        'LTV_60D': 'LTV_BASELINE_60D_to_LTV_BASELINE_12M',
                        'LTV_3M': 'LTV_BASELINE_03M_to_LTV_BASELINE_12M',
                        'LTV_4M': 'LTV_BASELINE_04M_to_LTV_BASELINE_12M',
                        'LTV_5M': 'LTV_BASELINE_05M_to_LTV_BASELINE_12M',
                        'LTV_6M': 'LTV_BASELINE_06M_to_LTV_BASELINE_12M',
                        'LTV_7M': 'LTV_BASELINE_07M_to_LTV_BASELINE_12M',
                        'LTV_8M': 'LTV_BASELINE_08M_to_LTV_BASELINE_12M',
                        'LTV_9M': 'LTV_BASELINE_09M_to_LTV_BASELINE_12M',
                        'LTV_10M': 'LTV_BASELINE_10M_to_LTV_BASELINE_12M',
                        'LTV_11M': 'LTV_BASELINE_11M_to_LTV_BASELINE_12M',
                        'LTV_12M': 'LTV_BASELINE_12M_to_LTV_BASELINE_12M'
                    }
                    
                    # Step 1: Adjust the iteration to handle the correct column names
                    tooltips = []  # Reset tooltips
                    
                    if not filtered_baseline_cohort_on_selected_mva_type.empty:
                        row = filtered_baseline_cohort_on_selected_mva_type.iloc[0]
                    
                        for i, label in enumerate(performance_period_labels):
                            tooltip_text = []
                    
                            # Get the corresponding realization column name from the mapping
                            realization_column = realization_column_mapping.get(label, None)
                            
                            # Debugging: Show the column name we are looking for
                            #st.write(f"Looking for column: '{realization_column}'")
                    
                            if realization_column:
                                # Check if the column exists in the row
                                if realization_column in row:
                                    realization_value = row[realization_column]
                                    baseline_values = [round(val, 2) for val in row[baseline_period_columns]]
                                    baseline_value_text = ['${:.2f}'.format(value) for value in baseline_values]
                    
                                    # Debugging: Display the retrieved value from the row
                                    #st.write(f"Realization value for '{realization_column}': {realization_value}")
                                    
                                    if realization_value is not None and not pd.isna(realization_value):
                                        tooltip_text.append(f"{label}:{baseline_value_text[i]} ({realization_value:.2f}%)")  # Add realization value
                                    else:
                                        # Handle missing or NaN values
                                        tooltip_text.append(f"{label}: N/A")
                                else:
                                    # If the column is not found, report the issue
                                    st.write(f"ERROR: Column '{realization_column}' not found in row!")
                            else:
                                # If the label doesn't have a corresponding column in the mapping, report it
                                st.write(f"ERROR: No mapping found for label '{label}'")
                    
                            # Add each label's tooltip to the list
                            tooltips.append(' '.join(tooltip_text))  # Concatenate text for clarity
                    
                    # Step 2: Prepare the x and y values for the scatter plot
                    baseline_dates = [date_mapping[label] for label in performance_period_labels]
            
                    
                    # Step 3: Prepare the hovertext using the realization values
                    hovertext_for_points = tooltips  # Each point will have the corresponding tooltip
                    # Step 4: Plot the figure with the tooltips
                    fig.add_trace(go.Scatter(
                        x=baseline_dates,
                        y=baseline_values,  # We are plotting the baseline values
                        mode='lines+markers+text',
                        name='Baseline',
                        text=['${:.2f}'.format(value) for value in baseline_values],  # Show value as text on hover
                        textposition="top center",  # Position the text
                        line=dict(color='blue'),
                        marker=dict(size=8),
                        hovertext=hovertext_for_points,  # Apply the individual tooltips for each point (realization value)
                        hoverinfo='text'  # Ensure it only shows the hovertext on hover
                    ))
                    
                    # Update chart layout
                    fig.update_layout( 
                        title=f"Baseline - {selected_mva_type} | {selected_mva_locale} | {selected_mva_device_group}",
                        xaxis_title="LTV Period",
                        yaxis_title="LTV Value ($)",
                        legend_title="Cohorts",
                        xaxis=dict(
                            tickvals=[date_mapping[label] for label in performance_period_labels],  # Map dates to labels
                            ticktext=performance_period_labels,  # Use the performance period labels for the x-axis text
                            showgrid=False
                        ),
                        template="plotly_white"
                    )
                    
                    # Display the chart
                    st.plotly_chart(fig)
            
            
                   
                    with st.expander("Glossary"):
                           st.markdown(f"""
                           ### Observed
                           Observed data for the Cohort of Performance. The current Cohort of Performance is **{selected_cohort}**.
                       
                           ### Extrapolated
                           The unavailable data for the Cohort of Performance is extrapolated. The current Cohort of Performance is **{selected_cohort}**.
                       
                           ### Baseline
                           The current baseline period is **{selected_baseline_desc}**.
                           """)
                      
                    with st.container():
                            st.subheader("Data")

                        
                    with st.expander("Show performance period data"):
                            for filtered_performance_cohort in filtered_performance_cohort_on_selected_mva_type:
                               # Convert to DataFrame
                               performance_df = pd.DataFrame(filtered_performance_cohort)
               
                               # Extract metadata columns (non-LTV columns)
                               meta_cols = ['MVA_NAME', 'MVA_LOCALE', 'MVA_DEVICE_GROUP']
                               meta_data = performance_df[meta_cols]
               
                               # Process LTV columns with their BASIS
                               combined_ltv_cols = {}
                               for col in performance_df.columns:
                                   if col.startswith("LTV_") and not col.endswith("_BASIS"):
                                       basis_col = f"{col}_BASIS"
                                       if basis_col in performance_df.columns:
                                           basis_value = performance_df[basis_col].iloc[0]  # Assume same basis per row
                                           new_col_name = f"{col} ({basis_value})"
                                           combined_ltv_cols[new_col_name] = performance_df[col]
               
                               # Combine metadata and transformed LTV columns
                               final_df = pd.concat([meta_data, pd.DataFrame(combined_ltv_cols)], axis=1)
               
                               st.write(final_df)
                    
                                
                    with st.expander("Show baseline period data"):
                                cohort_baseline_pandas = pd.DataFrame(filtered_baseline_cohort_on_selected_mva_type)
                                st.write(cohort_baseline_pandas)
        
            
            with tab_flow:
                
                    with st.container():
                        tab_flow = st.tabs(["1️⃣Baseline Historical","2️⃣Performance Period Correction", "3️⃣Seasonality Correction", "4️⃣Final Correction Share", "5️⃣LTV Comparison Charts"])
            
                    with tab_flow[0]:
                        
                        df = fetch_data_from_snowflake(query_for_static_view)
                        filtered_historical_df_on_selected_mva_type = df[df['MVA_NAME'].isin([selected_mva_type])]
                        #st.write(filtered_df_on_selected_mva_type)
                        show_baseline_histrical_df_in_table_formatted(filtered_historical_df_on_selected_mva_type, selected_mva_type)
                        #df0 = fetch_data_from_snowflake(query_for_baseline_period)
                        #st.dataframe(df0)
                        
                    with tab_flow[1]:
                        df1_query = flow_query1.format(selected_baseline_desc=selected_baseline_desc,correction_share=correction_share_table)
                        df1 = fetch_data_from_snowflake(df1_query)
                        st.dataframe(df1)
                    
                    with tab_flow[2]:
                        df2_query = flow_query2.format(selected_baseline_desc=selected_baseline_desc,correction_share=correction_share_table)
                        df2 = fetch_data_from_snowflake(df2_query)
                        st.dataframe(df2)
                
                    with tab_flow[3]:
                        df3_query = flow_query3.format(selected_baseline_desc=selected_baseline_desc,correction_share=correction_share_table)
                        df3 = fetch_data_from_snowflake(df3_query)
                        st.dataframe(df3)
                    
                    with tab_flow[4]:
                        query_chart_temp = query_chart \
                         .replace("{cohort_performance}", cohort_performance_table)
                        df_chart_full = fetch_data_from_snowflake(query_chart_temp)
                     
                        # Define required charts
                        chart_mapping = {
                            "app_download": ["all_devices", "native_android", "native_ios"],
                            "member_registration": ["all_devices"],
                            "trip_creation": ["all_devices"]
                        }
                     
                        # Get device groups for the selected MVA type
                        device_groups = chart_mapping.get(selected_mva_type, [])
                     
                        # Filter data for the selected MVA type
                        df_chart_filtered = df_chart_full[df_chart_full['MVA_NAME'] == selected_mva_type]
            
                        for device_group in device_groups:
                            df_chart = df_chart_filtered[df_chart_filtered['MVA_DEVICE_GROUP'] == device_group]
                     
                            if not df_chart.empty:
                                # Pivoting data for year-wise comparison
                                df_pivot = df_chart.pivot(index='MONTH', columns='YEAR', values='OBSERVED_LTV_60D')
                                df_pivot['CORRECTION'] = df_pivot[2024] / df_pivot[2023]
                                df_pivot['DIFFERENCE'] = ((df_pivot[2024] - df_pivot[2023]) / df_pivot[2024]) * 100
                                df_pivot = df_pivot.round(2)
                     
                                # Plot Chart
                                fig = go.Figure()
                     
                                # Add lines for LTV 2023 and 2024
                                fig.add_trace(go.Scatter(
                                    x=df_pivot.index, 
                                    y=df_pivot[2023], 
                                    mode='lines+markers', 
                                    name="2023 LTV", 
                                    line=dict(color='blue'),
                                    yaxis='y1'  # Use left vertical axis for 2023 data
                                ))
            
                                fig.add_trace(go.Scatter(
                                    x=df_pivot.index, 
                                    y=df_pivot[2024], 
                                    mode='lines+markers', 
                                    name="2024 LTV", 
                                    line=dict(color='red'),
                                    yaxis='y1'  # Use left vertical axis for 2024 data
                                ))
                     
                                # Add bar for correction ratio on right axis
                                fig.add_trace(go.Bar(
                                    x=df_pivot.index, 
                                    y=df_pivot['CORRECTION'], 
                                    name='Correction', 
                                    marker=dict(color='#fbbc04'), 
                                    opacity=0.7,
                                    yaxis='y2'  # Use right vertical axis for correction
                                ))
            
                                # Update Layout
                                fig.update_layout(
                                    title=f"{selected_mva_type} - {device_group} 60D Month-on-Month LTV",
                                    xaxis_title="Month",
                                    yaxis_title="LTV (2023 & 2024)",
                                    yaxis=dict(
                                        title="LTV (2023 & 2024)", 
                                        titlefont=dict(color='black'),
                                        tickfont=dict(color='black'),
                                        side="left"
                                    ),
                                    yaxis2=dict(
                                        title="Correction", 
                                        titlefont=dict(color='black'),
                                        tickfont=dict(color='black'),
                                        overlaying="y", 
                                        side="right"
                                    ),
                                    barmode="overlay",
                                    template="plotly_white",
                                    legend=dict(x=0.1, y=1.15, orientation="h")
                                )
                      
                                # Show Plot
                                st.plotly_chart(fig)

    else:
         # Create Tabs
                    tab_chart = create_tabs_only_baseline()
                    if(len(selected_basedline_description_only_baseline) > 0):
                        # Fetch the baseline data
                        query_for_baseline_period = query_for_baseline_period_template.format(selected_baseline_desc=selected_basedline_description_only_baseline[0],mva_ltv=mva_ltv_table)
                        baseline_df = fetch_data_from_snowflake(query_for_baseline_period)
                        baseline_cohort_df = baseline_df[baseline_df['MVA_NAME'].isin([selected_mva_type])]
                        
                        # Dropdown for MVA_LOCALE selection
                        mva_locale_values = baseline_cohort_df['MVA_LOCALE'].unique()
                        top_options = ['GLOBAL', 'US', 'ROW']
                        remaining_options = [locale for locale in mva_locale_values if locale not in top_options]
                        ordered_mva_locale_values = top_options + remaining_options
        
                        # Create columns for dropdowns
                        col1, col2 = st.columns(2)
        
                        with col1:
                            selected_mva_locale = st.selectbox(
                                "Select MVA Locale",
                                ordered_mva_locale_values,
                                index=ordered_mva_locale_values.index('GLOBAL') if 'GLOBAL' in ordered_mva_locale_values else 0
                            )
                        with col2:
                             selected_mva_device_group = st.selectbox(
                                 "Select MVA Device Group",
                                 options=baseline_cohort_df['MVA_DEVICE_GROUP'].unique(),
                                 index=list(baseline_cohort_df['MVA_DEVICE_GROUP'].unique()).index('all_devices')
                                 if 'all_devices' in baseline_cohort_df['MVA_DEVICE_GROUP'].unique() else 0
                             )
                            
                         # Filter the baseline and performance cohort data
                        filtered_baseline_cohort_on_selected_mva_type = baseline_cohort_df[
                             (baseline_cohort_df['MVA_NAME'] == selected_mva_type) & 
                             (baseline_cohort_df['MVA_LOCALE'] == selected_mva_locale) &
                             (baseline_cohort_df['MVA_DEVICE_GROUP'] == selected_mva_device_group)
                         ]
                        
                        if filtered_baseline_cohort_on_selected_mva_type.empty :
                             st.warning(f"No data available for selected locale {selected_mva_locale} and device group {selected_mva_device_group}.")
                        else:
                             st.write("")
        
                        if selected_basedline_description_only_baseline:
                            if len(selected_basedline_description_only_baseline) == 1:
                                st.text(f'The chart shows the LTV realization curve for {selected_basedline_description_only_baseline[0]} - Baseline Cohort')
                            else:
                                st.text("The chart shows the LTV realization curves for the following baseline cohorts:")
                                for desc in selected_basedline_description_only_baseline:
                                    st.markdown(f"- **{desc}**")
                        
                            # Setup date mapping
                            start_date = datetime.datetime(2023, 1, 1)
                            date_mapping = {
                                'LTV_15D': start_date + datetime.timedelta(days=15),
                                'LTV_30D': start_date + datetime.timedelta(days=30),
                                'LTV_45D': start_date + datetime.timedelta(days=45),
                                'LTV_60D': start_date + datetime.timedelta(days=60),
                                'LTV_3M': start_date + datetime.timedelta(days=90),
                                'LTV_4M': start_date + datetime.timedelta(days=120),
                                'LTV_5M': start_date + datetime.timedelta(days=150),
                                'LTV_6M': start_date + datetime.timedelta(days=180),
                                'LTV_7M': start_date + datetime.timedelta(days=210),
                                'LTV_8M': start_date + datetime.timedelta(days=240),
                                'LTV_9M': start_date + datetime.timedelta(days=270),
                                'LTV_10M': start_date + datetime.timedelta(days=300),
                                'LTV_11M': start_date + datetime.timedelta(days=330),
                                'LTV_12M': start_date + datetime.timedelta(days=360),
                            }
                        
                            fig = go.Figure()
                        
                            baseline_period_columns = [
                                'LTV_BASELINE_15D', 'LTV_BASELINE_30D', 'LTV_BASELINE_45D',
                                'LTV_BASELINE_60D', 'LTV_BASELINE_03M', 'LTV_BASELINE_04M',
                                'LTV_BASELINE_05M', 'LTV_BASELINE_06M', 'LTV_BASELINE_07M',
                                'LTV_BASELINE_08M', 'LTV_BASELINE_09M', 'LTV_BASELINE_10M',
                                'LTV_BASELINE_11M', 'LTV_BASELINE_12M'
                            ]
                            performance_period_labels = [
                                'LTV_15D', 'LTV_30D', 'LTV_45D', 'LTV_60D', 'LTV_3M', 'LTV_4M', 'LTV_5M', 'LTV_6M',
                                'LTV_7M', 'LTV_8M', 'LTV_9M', 'LTV_10M', 'LTV_11M', 'LTV_12M'
                            ]
                            realization_column_mapping = {
                                'LTV_15D': 'LTV_BASELINE_15D_to_LTV_BASELINE_12M',
                                'LTV_30D': 'LTV_BASELINE_30D_to_LTV_BASELINE_12M',
                                'LTV_45D': 'LTV_BASELINE_45D_to_LTV_BASELINE_12M',
                                'LTV_60D': 'LTV_BASELINE_60D_to_LTV_BASELINE_12M',
                                'LTV_3M': 'LTV_BASELINE_03M_to_LTV_BASELINE_12M',
                                'LTV_4M': 'LTV_BASELINE_04M_to_LTV_BASELINE_12M',
                                'LTV_5M': 'LTV_BASELINE_05M_to_LTV_BASELINE_12M',
                                'LTV_6M': 'LTV_BASELINE_06M_to_LTV_BASELINE_12M',
                                'LTV_7M': 'LTV_BASELINE_07M_to_LTV_BASELINE_12M',
                                'LTV_8M': 'LTV_BASELINE_08M_to_LTV_BASELINE_12M',
                                'LTV_9M': 'LTV_BASELINE_09M_to_LTV_BASELINE_12M',
                                'LTV_10M': 'LTV_BASELINE_10M_to_LTV_BASELINE_12M',
                                'LTV_11M': 'LTV_BASELINE_11M_to_LTV_BASELINE_12M',
                                'LTV_12M': 'LTV_BASELINE_12M_to_LTV_BASELINE_12M'
                            }
                        
                            colors = ['blue', 'orange', 'green', 'purple', 'red', 'teal', 'cyan', 'magenta']
                        
                            for idx, desc in enumerate(selected_basedline_description_only_baseline):
                                query = query_for_baseline_period_template.format(selected_baseline_desc=desc,mva_ltv=mva_ltv_table)
                                baseline_df = fetch_data_from_snowflake(query)
                                baseline_cohort_df = baseline_df[baseline_df['MVA_NAME'].isin([selected_mva_type])]
                                filtered_baseline = baseline_cohort_df[
                                    (baseline_cohort_df['MVA_LOCALE'] == selected_mva_locale) &
                                    (baseline_cohort_df['MVA_DEVICE_GROUP'] == selected_mva_device_group)
                                ]
                                
                                if filtered_baseline.empty:
                                    continue
                        
                                row = filtered_baseline.iloc[0]
                        
                                # Add realization %
                                for column in baseline_period_columns:
                                    col_name = f'{column}_to_LTV_BASELINE_12M'
                                    row[col_name] = (row[column] / row['LTV_BASELINE_12M']) * 100 if row['LTV_BASELINE_12M'] != 0 else None
                        
                                # Create tooltips
                                tooltips = [
                                    f"{label}: {row[realization_column_mapping[label]]:.2f}%" if pd.notna(row[realization_column_mapping[label]]) else f"{label}: N/A"
                                    for label in performance_period_labels
                                ]
                        
                                baseline_values = [round(row[col], 2) for col in baseline_period_columns]
                                baseline_dates = [date_mapping[label] for label in performance_period_labels]
                        
                                fig.add_trace(go.Scatter(
                                    x=baseline_dates,
                                    y=baseline_values,
                                    mode='lines+markers+text',
                                    name=desc,  # Show cohort label as line name
                                    text=['${:.2f}'.format(v) for v in baseline_values],
                                    textposition="top center",
                                    line=dict(color=colors[idx % len(colors)]),
                                    marker=dict(size=8),
                                    hovertext=tooltips,
                                    hoverinfo='text'
                                ))
                        
                            fig.update_layout(
                                title=f"Baseline - {selected_mva_type} | {selected_mva_locale} | {selected_mva_device_group}",
                                xaxis_title="LTV Period",
                                yaxis_title="LTV Value ($)",
                                legend_title="Cohorts",
                                xaxis=dict(
                                    tickvals=[date_mapping[label] for label in performance_period_labels],
                                    ticktext=performance_period_labels,
                                    showgrid=False
                                ),
                                template="plotly_white"
                            )
                        
                            st.plotly_chart(fig)
        
        
                    
                    

#---------------------------------------------------------------

page_names_to_bounty_types = {
        "📱 App Download for Members": "app_download",
        "🧑‍🤝‍🧑 Member Registration": "member_registration",
        "✈️ Trip Creation": "trip_creation"  
    }
    
# is_tamg = st.toggle("Show TA Only View", value=False)  # Default: TAMG

# selected_mode = "TA_ONLY" if is_tamg else "TAMG"
selected_radio_button = st.radio("Select the MVA", list(page_names_to_bounty_types.keys()))
if selected_mode == "TAMG":
        st.info("👀 This data includes Viator revenue!")
else:
        st.info("👀 This data is for TA only!")

selected_mva_type = page_names_to_bounty_types[selected_radio_button or "📱 App"]
    
with st.spinner(f"Loading data for {selected_radio_button}..."):
     show_bounty_metrics(selected_mva_type) 