# WIP | Copy of App Cohort Tracking Dashboard - CTA Validation - VK
from snowflake.snowpark.context import get_active_session
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
import pandas as pd
import altair as alt
st.set_page_config(
    page_title="My Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
    )


st.title("💰 App Cohort Tracking Dashboard")

# Fetch available baseline periods with descriptions
monthly_view_query = """ 
WITH cohort_agg_device AS (   
  SELECT
    {select_channel_column}
    TO_CHAR(TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY'), 'YYYY-MM') AS cohort_month,
    TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY') AS cohort_date,
    CTA_DEVICE_GROUP,
    SUM(EXPECTED_MVA_INCREMENTAL_VALUE_12M) AS expected_incremental_value_12m,
    SUM(EXTRAPOLATED_INCREMENTAL_12M) AS extrapolated_incremental_12m,
    COUNT(DISTINCT CTA_CAMPAIGN) AS campaign_count,
    COUNT(*) AS record_count,
    MAX(COHORT_MATURITY) AS cohort_maturity,
    SUM(CTA_DEVICES_COUNT) AS devices_count,
    SUM(TOTAL_CAMPAIGN_COST) AS total_cost,
    SUM(OBSERVED_INCREMENTAL_VALUE) AS observed_incremental_value
  FROM user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
  WHERE 
    CAMPAIGN_DASH_STATUS = True
    AND TOTAL_CAMPAIGN_COST > 0 AND TOTAL_CAMPAIGN_COST IS NOT NULL
    AND CTA_NAME = {select_cta_name}
    AND CTA_DEVICE_GROUP IN ('native_android', 'native_ios')
  GROUP BY {group_by_clause}, CTA_DEVICE_GROUP
),

cohort_agg_overall AS (
  SELECT
    {select_channel_column}
    TO_CHAR(TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY'), 'YYYY-MM') AS cohort_month,
    TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY') AS cohort_date,
    SUM(EXPECTED_MVA_INCREMENTAL_VALUE_12M) AS expected_incremental_value_12m,
    SUM(EXTRAPOLATED_INCREMENTAL_12M) AS extrapolated_incremental_12m,
    COUNT(DISTINCT CTA_CAMPAIGN) AS campaign_count,
    COUNT(*) AS record_count,
    MAX(COHORT_MATURITY) AS cohort_maturity,
    SUM(CTA_DEVICES_COUNT) AS devices_count,
    SUM(TOTAL_CAMPAIGN_COST) AS total_cost,
    SUM(OBSERVED_INCREMENTAL_VALUE) AS observed_incremental_value
  FROM user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
  WHERE 
    CAMPAIGN_DASH_STATUS = True
    AND TOTAL_CAMPAIGN_COST > 0 AND TOTAL_CAMPAIGN_COST IS NOT NULL
    AND CTA_NAME = {select_cta_name}
    AND CTA_DEVICE_GROUP IN ('native_android', 'native_ios')
  GROUP BY {group_by_clause}
)
,combined AS (

  SELECT
    {select_channel_column}
    'Overall' AS device,
    TO_CHAR(cohort_date, 'Mon YYYY') AS COHORT,
    devices_count,
    total_cost,
    observed_incremental_value,
    expected_incremental_value_12m,
    extrapolated_incremental_12m,
    cohort_maturity,
    cohort_date
  FROM cohort_agg_overall

  UNION ALL

  SELECT
    {select_channel_column}
    CTA_DEVICE_GROUP AS device,
    TO_CHAR(cohort_date, 'Mon YYYY') AS COHORT,
    devices_count,
    total_cost,
    observed_incremental_value,
    expected_incremental_value_12m,
    extrapolated_incremental_12m,
    cohort_maturity,
    cohort_date
  FROM cohort_agg_device
)

SELECT
  {select_channel_column}
  device,
  TO_CHAR(cohort_date, 'Mon YYYY') AS COHORT,
  devices_count AS TOTAL_INSTALL_COUNT,
  '$' || ROUND(total_cost / devices_count, 2) AS "Avg CPI",
  ROUND(total_cost, 2) AS TOTAL_COST,
  ROUND(observed_incremental_value, 2) AS OBSERVED_INCREMENTAL_VALUE,
  ROUND(expected_incremental_value_12m, 2) AS EXPECTED_APP_INCREMENTAL_VALUE_12M,
  ROUND(expected_incremental_value_12m / total_cost * 100, 2) || '%' AS EXPECTED_APP_INCREMENTAL_VALUE_ROAS_12M,
  ROUND(extrapolated_incremental_12m, 2) AS EXTRAPOLATED_12M_INCREMENTAL,
  ROUND(extrapolated_incremental_12m / total_cost * 100, 2) || '%' AS EXTRAPOLATED_ROAS,
  cohort_maturity
FROM combined
ORDER BY cohort_date ASC, device;

"""

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
    {mva_ltv}

    ORDER BY VALIDITY_START_DATE DESC
    ;
"""
available_performance_cohort_query = """
SELECT DISTINCT COHORT_START_DATE 
FROM 
{cohort_performance}

;
"""

campaign_meta_query=""" 
SELECT
    DISTINCT COHORT_DESCRIPTION, CTA_NAME, CTA_LOCALE,CTA_DEVICE_GROUP,CTA_CAMPAIGN,MEMBERSHIP_COHORT
FROM 
user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
WHERE 
    TOTAL_CAMPAIGN_COST > 0 AND TOTAL_CAMPAIGN_COST IS NOT NULL
     and CAMPAIGN_DASH_STATUS = 'true'
;
"""
all_campaign_query_template = """
SELECT
  COHORT_DESCRIPTION AS COHORT,
  CTA_CHANNEL,
  CTA_CAMPAIGN AS CAMPAIGN,
  CTA_LOCALE AS LOCALE,
  CTA_DEVICE_GROUP AS DEVICE_GROUP,
  LOWER(MEMBERSHIP_COHORT) AS MEMBERSHIP_COHORT,
  CTA_DEVICES_COUNT AS TOTAL_INSTALL_COUNT,
  '$' || ROUND(TOTAL_CAMPAIGN_COST / CTA_DEVICES_COUNT, 2) AS "Avg CPI",
  TOTAL_CAMPAIGN_COST AS TOTAL_COST,
  SUM(OBSERVED_INCREMENTAL_VALUE) AS OBSERVED_INCREMENTAL_VALUE,
  EXPECTED_MVA_INCREMENTAL_VALUE_12M AS EXPECTED_INCREMENTAL_VALUE_12M,
  ROUND(expected_incremental_value_12m / total_cost * 100, 2) || '%' AS EXPECTED_APP_INCREMENTAL_VALUE_ROAS_12M,
  EXTRAPOLATED_INCREMENTAL_12M,
  CASE 
    WHEN 
      cohort_maturity IN ('15D','30D','45D','60D','3M') -- under 4 months
      AND EXTRAPOLATED_INCREMENTAL_ROAS > expected_mva_incremental_value_roas_12m
    THEN CONCAT(
        ROUND((1.2 * OBSERVED_INCREMENTAL_VALUE / total_campaign_cost) * 100, 2) || '%',
        ' - ',
        ROUND(EXTRAPOLATED_INCREMENTAL_ROAS * 100, 2) || '%'
    )
    ELSE ROUND(EXTRAPOLATED_INCREMENTAL_ROAS * 100, 2) || '%'
  END AS EXTRAPOLATED_INCREMENTAL_ROAS,
  COHORT_MATURITY,
  CASE 
        WHEN ON_TRACK_TO_EXCEED_ROAS_TARGET = TRUE THEN 'ON TRACK'
        ELSE 'OFF TRACK'
  END AS ON_TRACK_STATUS

FROM user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
WHERE 
    CAMPAIGN_DASH_STATUS = True
    AND TOTAL_CAMPAIGN_COST > 0 AND TOTAL_CAMPAIGN_COST IS NOT NULL
    AND CTA_NAME = {select_cta_name}
GROUP BY ALL
ORDER BY 
  CAMPAIGN,
  TO_DATE(COHORT, 'MON_YYYY') ASC,
  LOCALE,
  DEVICE_GROUP,
  CASE 
    WHEN MEMBERSHIP_COHORT = 'overall' THEN 1
    WHEN MEMBERSHIP_COHORT = 'member' THEN 2
    WHEN MEMBERSHIP_COHORT = 'non-member' THEN 3
  END ASC;
"""
on_track_query_template = """
SELECT
  COHORT_DESCRIPTION AS COHORT,
  CTA_CAMPAIGN AS CAMPAIGN,
  CTA_LOCALE AS LOCALE,
  CTA_DEVICE_GROUP AS DEVICE_GROUP,
  LOWER(MEMBERSHIP_COHORT) AS MEMBERSHIP_COHORT,
  CTA_DEVICES_COUNT AS TOTAL_INSTALL_COUNT,
  '$' || ROUND(TOTAL_CAMPAIGN_COST / CTA_DEVICES_COUNT, 2) AS "Avg CPI",
  TOTAL_CAMPAIGN_COST AS TOTAL_COST,
  SUM(OBSERVED_INCREMENTAL_VALUE) AS OBSERVED_INCREMENTAL_VALUE,
  EXPECTED_MVA_INCREMENTAL_VALUE_12M AS EXPECTED_INCREMENTAL_VALUE_12M,
  ROUND(expected_incremental_value_12m / total_cost * 100, 2) || '%' AS EXPECTED_APP_INCREMENTAL_VALUE_ROAS_12M,
  EXTRAPOLATED_INCREMENTAL_12M,
  case 
        when (cohort_maturity in ('15D','30D','45D','60D','3M') and 
        EXTRAPOLATED_INCREMENTAL_ROAS >= expected_mva_incremental_value_roas_12m)
        then concat(ROUND((1.2 * OBSERVED_INCREMENTAL_VALUE / nullif(total_campaign_cost,0)) * 100,2) || '%'
        , ' - ', ROUND(EXTRAPOLATED_INCREMENTAL_ROAS * 100, 2) || '%') 
        else ROUND(EXTRAPOLATED_INCREMENTAL_ROAS * 100, 2) || '%'
        
  end as EXTRAPOLATED_INCREMENTAL_ROAS,
  COHORT_MATURITY,
  CASE 
        WHEN ON_TRACK_TO_EXCEED_ROAS_TARGET = TRUE THEN 'ON TRACK'
        ELSE 'OFF TRACK'
  END AS ON_TRACK_STATUS

FROM user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov 
WHERE
  COHORT_DESCRIPTION IN ({cohorts})
  AND CTA_LOCALE =  '{locale}'
  AND CTA_CAMPAIGN IN ({campaigns})
  AND CTA_DEVICE_GROUP = '{device_groups}'
  AND MEMBERSHIP_COHORT IN ({member_type})
  AND CTA_NAME IN ({selected_cta_type})
  AND CTA_DEVICES_COUNT is not null
GROUP BY ALL
ORDER BY 
  CAMPAIGN,
  TO_DATE(COHORT, 'MON_YYYY') ASC,
  LOCALE,
  DEVICE_GROUP,
  CASE 
    WHEN MEMBERSHIP_COHORT = 'overall' THEN 1
    WHEN MEMBERSHIP_COHORT = 'member' THEN 2
    WHEN MEMBERSHIP_COHORT = 'non-member' THEN 3
  END ASC;
"""
glossary_query_template = """
select 
    *
from 
    ANALYTICS.ACIES.CTA_TABLE_DESCRIPTION
;
"""
query_for_baseline_period_template = """
    SELECT 
        MVA_NAME,
        MVA_LOCALE,
        MVA_DEVICE_GROUP,
        LTV_BASELINE_15D,
        LTV_BASELINE_30D,
        LTV_BASELINE_45D,
        LTV_BASELINE_60D,
        LTV_BASELINE_03M,
        LTV_BASELINE_04M,
        LTV_BASELINE_05M,
        LTV_BASELINE_06M,
        LTV_BASELINE_07M,
        LTV_BASELINE_08M,
        LTV_BASELINE_09M,
        LTV_BASELINE_10M,
        LTV_BASELINE_11M,
        LTV_BASELINE_12M
    FROM 
    {mva_ltv}
    WHERE 

        BASE_PERIOD_DESCRIPTION = '{selected_baseline_desc}'
        AND MVA_LOCALE = '{locale}' 
        AND MVA_DEVICE_GROUP = '{device_groups}'
        AND MVA_NAME = '{selected_mva_type}'
"""

flow_query_template = """
SELECT
  COHORT_DESCRIPTION AS COHORT,
  COHORT_MATURITY,
  CTA_CAMPAIGN AS CAMPAIGN,
  CTA_LOCALE AS LOCALE,
  CTA_DEVICE_GROUP AS DEVICE_GROUP,
  LOWER(MEMBERSHIP_COHORT) AS MEMBERSHIP_COHORT,
  SUM(TOTAL_CAMPAIGN_COST) AS TOTAL_COST,
  SUM(OBSERVED_VALUE) AS OBSERVED_PROFIT,
  SUM(OBSERVED_INCREMENTAL_VALUE) AS OBSERVED_INCREMENTAL_VALUE,
  ROUND(OBSERVED_INCREMENTAL_ROAS * 100, 2) || '%' AS OBSERVED_INCREMENTAL_ROAS,
  SUM(EXPECTED_MVA_LTV_12M) AS EXPECTED_APP_LTV_12M,
  SUM(EXPECTED_MVA_INCREMENTAL_VALUE_12M) AS EXPECTED_APP_INCREMENTAL_VALUE_12M,
  ROUND(EXPECTED_MVA_INCREMENTAL_VALUE_ROAS_12M * 100, 2) || '%' AS EXPECTED_APP_INCREMENTAL_VALUE_ROAS_12M,
  SUM(EXTRAPOLATED_INCREMENTAL_12M) AS EXTRAPOLATED_INCREMENTAL_12M,
  MVA_LTV_ID
FROM 
user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
WHERE 
  COHORT_DESCRIPTION IN ({cohorts})
  AND CTA_LOCALE = '{locale}' 
  AND CTA_CAMPAIGN IN ({campaigns})
  AND CTA_DEVICE_GROUP = '{device_groups}'
  AND MEMBERSHIP_COHORT IN ({member_type})
  AND CTA_NAME IN ({selected_cta_type})
GROUP BY ALL
ORDER BY 
CTA_CAMPAIGN,
TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY') ASC,
COHORT_MATURITY,
CTA_LOCALE,
CTA_DEVICE_GROUP,
   CASE 
        WHEN MEMBERSHIP_COHORT = 'overall' THEN 1
        WHEN MEMBERSHIP_COHORT = 'member' THEN 2
        WHEN MEMBERSHIP_COHORT = 'non-member' THEN 3
    END ASC
;
"""
active_users_query_template ="""
WITH member_percent_cte AS (
  SELECT
    CTA_CAMPAIGN,
    COHORT_DESCRIPTION,
    CTA_LOCALE,
    CTA_DEVICE_GROUP,
    SUM(CASE WHEN LOWER(MEMBERSHIP_COHORT) = 'member' THEN CTA_DEVICES_COUNT ELSE 0 END) AS member_count,
    SUM(CASE WHEN LOWER(MEMBERSHIP_COHORT) = 'overall' THEN CTA_DEVICES_COUNT ELSE 0 END) AS overall_count
  FROM user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
  GROUP BY CTA_CAMPAIGN, COHORT_DESCRIPTION, CTA_LOCALE, CTA_DEVICE_GROUP
)

SELECT 
 main.COHORT_DESCRIPTION AS COHORT,
 main.COHORT_MATURITY,
 main.CTA_CAMPAIGN AS CAMPAIGN,
 main.CTA_LOCALE AS LOCALE,
 main.CTA_DEVICE_GROUP AS DEVICE_GROUP,
 LOWER(main.MEMBERSHIP_COHORT) AS MEMBERSHIP_COHORT,
 CASE WHEN MEMBERSHIP_COHORT = 'OVERALL' THEN
    ROUND(100.0 * COALESCE(mp.member_count, 0) / NULLIF(mp.overall_count, 0), 2) || '%' 
    ELSE 'None'
 END AS MEMBER_PERCENTAGE,
 main.CTA_DEVICES_COUNT AS DEVICES_COUNT,
 main.CTA_USERS_COUNT AS USERS_COUNT,
 main.CTA_QUALIFYING_ACTION_COUNT AS QUALIFIED_NEW_INSTALLS,
 main.CTA_NON_QUALIFYING_ACTION_COUNT AS REINSTALL,
 main.CTA_ACTIVE_USERS_COUNT AS ACTIVE_USERS,
 (main.CTA_ACTIVE_USERS_COUNT * 100.0 / NULLIF(main.CTA_QUALIFYING_ACTION_COUNT, 0)) AS ACTIVE_USERS_PERCENT,
 (main.CTA_NON_QUALIFYING_ACTION_COUNT * 100.0 / NULLIF(main.CTA_USERS_COUNT, 0)) AS REINSTALL_PERCENT
FROM 
user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov main
LEFT JOIN member_percent_cte mp
  ON main.COHORT_DESCRIPTION = mp.COHORT_DESCRIPTION
  AND main.CTA_LOCALE = mp.CTA_LOCALE
  AND main.CTA_DEVICE_GROUP = mp.CTA_DEVICE_GROUP
  AND main.CTA_CAMPAIGN = mp.CTA_CAMPAIGN
  
WHERE 
      main.COHORT_DESCRIPTION IN ({cohorts})
  AND main.CTA_LOCALE = '{locale}'
  AND main.CTA_CAMPAIGN IN ({campaigns})
  AND main.CTA_DEVICE_GROUP = '{device_groups}'
  AND main.MEMBERSHIP_COHORT IN ({member_type})
  AND main.CTA_NAME IN ({selected_cta_type})
GROUP BY ALL
ORDER BY 
main.CTA_CAMPAIGN,
TO_DATE(main.COHORT_DESCRIPTION, 'MON_YYYY') ASC,
main.COHORT_MATURITY,
main.CTA_LOCALE,
main.CTA_DEVICE_GROUP,
    CASE 
        WHEN MEMBERSHIP_COHORT = 'overall' THEN 1
        WHEN MEMBERSHIP_COHORT = 'member' THEN 2
        WHEN MEMBERSHIP_COHORT = 'non-member' THEN 3
    END ASC
  ;
"""
realization_query_template = """
SELECT 
    COHORT_DESCRIPTION,
    CTA_CAMPAIGN,
    CTA_LOCALE,
    CTA_DEVICE_GROUP,
    MEMBERSHIP_COHORT,
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
    EXTRAPOLATED_VALUE_12M AS LTV_12M,
    'EXTRAPOLATED' AS LTV_12M_BASIS,
    MVA_LTV_ID
    
FROM
   user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
WHERE 
    COHORT_DESCRIPTION IN ({cohorts})
    AND CTA_CAMPAIGN IN ({campaigns})
    AND CTA_LOCALE = '{locale}'
    AND CTA_DEVICE_GROUP = '{device_groups}'
    AND MEMBERSHIP_COHORT IN ({member_type})
    AND CTA_NAME IN ({selected_cta_type})
GROUP BY ALL
ORDER BY 
CTA_CAMPAIGN,
COHORT_DESCRIPTION,
CTA_LOCALE,
CTA_DEVICE_GROUP,
    CASE 
        WHEN MEMBERSHIP_COHORT = 'OVERALL' THEN 1
        WHEN MEMBERSHIP_COHORT = 'MEMBER' THEN 2
        WHEN MEMBERSHIP_COHORT = 'NON-MEMBER' THEN 3
    END
;
"""



realization_ltv_query_template = """
SELECT 
    COHORT_DESCRIPTION,
    CTA_CAMPAIGN,
    CTA_LOCALE,
    CTA_DEVICE_GROUP,
    MEMBERSHIP_COHORT,
    SUM(CTA_QUALIFYING_ACTION_COUNT) AS QUALIFIED_USERS,

    (CASE WHEN SUM(OBSERVED_LTV_15D) IS NOT NULL THEN SUM(OBSERVED_LTV_15D) ELSE SUM(EXTRAPOLATED_LTV_15D) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_15D,
    CASE WHEN SUM(OBSERVED_LTV_15D) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_15D_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_30D) IS NOT NULL THEN SUM(OBSERVED_LTV_30D) ELSE SUM(EXTRAPOLATED_LTV_30D) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_30D,
    CASE WHEN SUM(OBSERVED_LTV_30D) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_30D_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_45D) IS NOT NULL THEN SUM(OBSERVED_LTV_45D) ELSE SUM(EXTRAPOLATED_LTV_45D) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_45D,
    CASE WHEN SUM(OBSERVED_LTV_45D) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_45D_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_60D) IS NOT NULL THEN SUM(OBSERVED_LTV_60D) ELSE SUM(EXTRAPOLATED_LTV_60D) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_60D,
    CASE WHEN SUM(OBSERVED_LTV_60D) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_60D_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_03M) IS NOT NULL THEN SUM(OBSERVED_LTV_03M) ELSE SUM(EXTRAPOLATED_LTV_03M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_03M,
    CASE WHEN SUM(OBSERVED_LTV_03M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_03M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_04M) IS NOT NULL THEN SUM(OBSERVED_LTV_04M) ELSE SUM(EXTRAPOLATED_LTV_04M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_04M,
    CASE WHEN SUM(OBSERVED_LTV_04M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_04M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_05M) IS NOT NULL THEN SUM(OBSERVED_LTV_05M) ELSE SUM(EXTRAPOLATED_LTV_05M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_05M,
    CASE WHEN SUM(OBSERVED_LTV_05M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_05M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_06M) IS NOT NULL THEN SUM(OBSERVED_LTV_06M) ELSE SUM(EXTRAPOLATED_LTV_06M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_06M,
    CASE WHEN SUM(OBSERVED_LTV_06M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_06M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_07M) IS NOT NULL THEN SUM(OBSERVED_LTV_07M) ELSE SUM(EXTRAPOLATED_LTV_07M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_07M,
    CASE WHEN SUM(OBSERVED_LTV_07M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_07M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_08M) IS NOT NULL THEN SUM(OBSERVED_LTV_08M) ELSE SUM(EXTRAPOLATED_LTV_08M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_08M,
    CASE WHEN SUM(OBSERVED_LTV_08M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_08M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_09M) IS NOT NULL THEN SUM(OBSERVED_LTV_09M) ELSE SUM(EXTRAPOLATED_LTV_09M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_09M,
    CASE WHEN SUM(OBSERVED_LTV_09M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_09M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_10M) IS NOT NULL THEN SUM(OBSERVED_LTV_10M) ELSE SUM(EXTRAPOLATED_LTV_10M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_10M,
    CASE WHEN SUM(OBSERVED_LTV_10M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_10M_BASIS,

    (CASE WHEN SUM(OBSERVED_LTV_11M) IS NOT NULL THEN SUM(OBSERVED_LTV_11M) ELSE SUM(EXTRAPOLATED_LTV_11M) END) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_11M,
    CASE WHEN SUM(OBSERVED_LTV_11M) IS NOT NULL THEN 'OBSERVED' ELSE 'EXTRAPOLATED' END AS LTV_11M_BASIS,

    SUM(EXTRAPOLATED_VALUE_12M) / SUM(CTA_QUALIFYING_ACTION_COUNT) AS LTV_12M,
    'EXTRAPOLATED' AS LTV_12M_BASIS

FROM
   user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov

WHERE 
    COHORT_DESCRIPTION IN ({cohorts})
    AND CTA_CAMPAIGN IN ({campaigns})
    AND CTA_LOCALE = '{locale}'
    AND CTA_DEVICE_GROUP = '{device_groups}'
    AND MEMBERSHIP_COHORT IN ({member_type})
    AND CTA_NAME IN ({selected_cta_type})
GROUP BY ALL
ORDER BY 
CTA_CAMPAIGN,
COHORT_DESCRIPTION,
CTA_LOCALE,
CTA_DEVICE_GROUP,
    CASE 
        WHEN MEMBERSHIP_COHORT = 'OVERALL' THEN 1
        WHEN MEMBERSHIP_COHORT = 'MEMBER' THEN 2
        WHEN MEMBERSHIP_COHORT = 'NON-MEMBER' THEN 3
    END
;
"""




def fetch_data_from_snowflake(query):
    session = get_active_session()  # Retrieve the active Snowflake session
    df = session.sql(query).to_pandas()  # Fetch the query results as a Pandas DataFrame
    return df

def render_table_with_colors(df):
    import pandas as pd

    columns = df.columns.tolist()
    grouped_headers = {
        "EXPECTED": {
            "columns": ["EXPECTED_INCREMENTAL_VALUE_12M", "EXPECTED_INCREMENTAL_VALUE_ROAS_12M","EXPECTED_APP_LTV_12M","EXPECTED_APP_INCREMENTAL_VALUE_12M","EXPECTED_APP_INCREMENTAL_VALUE_ROAS_12M"],
            "color": "#4a90e2"
        },
        "EXTRAPOLATED": {
            "columns": ["EXTRAPOLATED_INCREMENTAL_12M", "EXTRAPOLATED_INCREMENTAL_ROAS","EXTRAPOLATED_INCREMENTAL_12M","EXTRAPOLATED_12M_INCREMENTAL","EXTRAPOLATED_ROAS"],
            "color": "#7ed6df"
        },
        "OBSERVED": {
        "columns": ["OBSERVED_PROFIT", "OBSERVED_INCREMENTAL_VALUE", "OBSERVED_INCREMENTAL_ROAS"],
        "color": "#f3a683"
    }
    }


    # Clean display columns
    display_columns = []
    for col in columns:
        display_col = col
        for group_name in grouped_headers:
            if col in grouped_headers[group_name]["columns"]:
                display_col = col.replace(f"{group_name}_", "")
                break
        display_columns.append(display_col)

    df_display = df.copy()
    df_display.columns = display_columns

    def format_number(val):
        try:
            val_float = float(val)
            return f"{val_float:,.2f}"
        except (ValueError, TypeError):
            return val
    
    def format_whole_number(val):
        try:
            val_int = int(float(val))
            return f"{val_int:,}"
        except (ValueError, TypeError):
            return val
    
    # Define columns to format as whole numbers
    whole_number_columns = ["DEVICES_COUNT", "USERS_COUNT", "QUALIFIED_NEW_INSTALLS", "REINSTALL"	,"ACTIVE_USERS","TOTAL_INSTALL_COUNT"]
    number_columns = ["DEVICES_COUNT", "USERS_COUNT", "QUALIFIED_NEW_INSTALLS", "REINSTALL"	,"ACTIVE_USERS", "INCREMENTAL_VALUE_12M", 
                      "INCREMENTAL_VALUE_ROAS_12M","APP_LTV_12M","APP_INCREMENTAL_VALUE_ROAS_12M", "INCREMENTAL_12M", "INCREMENTAL_ROAS",
                      "PROFIT", "INCREMENTAL_VALUE", "APP_INCREMENTAL_VALUE_12M", "TOTAL_COST", "ACTIVE_USERS_PERCENT",	"REINSTALL_PERCENT",
                      "Avg CPI", "ROAS", "TOTAL_INSTALL_COUNT","12M_INCREMENTAL"
                     ]
    # Apply different formatting functions
    for col in df_display.columns:
        if col in whole_number_columns:
            df_display[col] = df_display[col].apply(format_whole_number)
        else:
            df_display[col] = df_display[col].apply(format_number)

    # Highlight status cells
    def highlight_status(val):
        if isinstance(val, str):
            if "ON TRACK" in val.upper():
                return f"<span style='background-color:#e6f4ea; color:#0f9d58; padding:2px 6px; border-radius:4px;'>🟢 {val}</span>"
            elif "OFF TRACK" in val.upper():
                return f"<span style='background-color:#fdecea; color:#d93025; padding:2px 6px; border-radius:4px;'>🔴 {val}</span>"
        return val

    existing_whole_number_cols = [col for col in number_columns if col in df_display.columns]
    df_display = df_display.applymap(highlight_status)
    styled_df = (
        df_display.style
        .set_table_styles([
            {
                'selector': 'th',
                'props': [
                    ('background-color', 'grey'),
                    ('font-weight', 'bold'),
                    ('color', 'white'),
                    ('white-space', 'normal'),
                    ('word-break', 'break-word'),
                    ('text-align', 'center'),
                    ('border', '1px solid #ddd'),
                    ('padding', '8px'),
                    ('font-size', '12px')  # 👈 reduced font size for header
                ]
            }
        ])
        .hide(axis="index")
        .set_properties(**{
        'text-align': 'left',  # or 'center' or 'left'
        'padding': '6px'
    })
        .set_properties(subset=existing_whole_number_cols, **{'text-align': 'right'})
    )
    html = styled_df.to_html(escape=False)

    # Merged header row
    merged_row = "<tr>"
    i = 0
    while i < len(columns):
        col = columns[i]
        matched = False
        for group_name, group_info in grouped_headers.items():
            group_cols = group_info["columns"]
            if col in group_cols:
                # Count how many group columns match consecutively
                colspan = 0
                for j in range(i, len(columns)):
                    if columns[j] in group_cols:
                        colspan += 1
                    else:
                        break
                merged_row += (
                    f'<th colspan="{colspan}" style="background-color: {group_info["color"]}; '
                    f'color: white; font-weight: bold; text-align: center; border: 1px solid #ddd; padding: 8px;">{group_name}</th>'
                )
                i += colspan
                matched = True
                break
        if not matched:
            merged_row += '<th style="background-color: transparent; border: 1px solid transparent;"></th>'
            i += 1
    merged_row += "</tr>"


    # Dynamically calculate column widths based on max character length
    col_defs = []
    for idx, col in enumerate(df_display.columns):
        # Estimate character width
        max_char_len = df_display[col].astype(str).map(len).max()
        col_name_len = len(str(col))
        max_len = max(max_char_len, col_name_len)

        # Estimate width in pixels (approx. 7px per character, capped reasonably)
        width = max(80, min(280, max_len * 7))
        col_defs.append(f'<col style="min-width: {width}px;">')

    colgroup_html = "<colgroup>" + "".join(col_defs) + "</colgroup>"
    html = html.replace("<table", "<table style='width: 100%; border-collapse: collapse;'")
    html = html.replace("<thead>", colgroup_html + "<thead>" + merged_row)

    return html



# Helper function to format numbers
def format_number(value):
    if value > 999_999_999:
        return f"{value / 1_000_000_000:.2f}b"
    elif value > 999_999:
        return f"{value / 1_000_000:.2f}m"
    elif value > 100:
        return f"{value / 1_000:.2f}k"
    else:
        return f"{value:.2f}"
        
  
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
    tab_monthly_view,tab_all_campaign_view,tab_campaign_view,tab_detailed_view,tab_chart, tab_sql,tab_glossary= st.tabs(
            [ "📅 Monthly View","🧾 All Campaign View","🗃 Campaign View", "💻 Detailed View", "📈 Realization Chart ","🧮 SQL Code","🔤 Glossary"])
    return tab_monthly_view,tab_all_campaign_view,tab_campaign_view,tab_detailed_view,tab_chart, tab_sql,tab_glossary



def show_sql_code(queries):
    """
    Display each SQL query in a separate expandable code section in Streamlit.

    Parameters:
    - queries: dict or str
        A single SQL string or a dictionary of query_name: query_string pairs.
    """
    if isinstance(queries, dict):
        for name, query in queries.items():
            with st.expander(label=f"📄 {name}", expanded=False):
                st.code(query.strip(), language="sql")
    elif isinstance(queries, str):
        with st.expander(label="📄 SQL Query", expanded=False):
            st.code(queries.strip(), language="sql")
    else:
        st.warning("Unsupported query format. Provide a string or a dictionary of SQL queries.")


def show_df_in_table_formatted(df):
    if not df.empty:
        # Get the HTML representation of the styled table
        styled_table = render_table_with_colors(df)
        
        # Display the styled HTML table in Streamlit using markdown
        st.markdown(styled_table, unsafe_allow_html=True)  # No need for .render() here
    else:
        st.write("Please select locales to display.")



def format_for_sql_in(values):
    """Helper to format list of values for SQL IN clause"""
    return ", ".join(f"'{v}'" for v in values)
    
def run_query(query):
    session = get_active_session()  # Use the same active Snowflake session
    session.sql(query).collect()   # Run the query (no need to fetch data)

def show_bounty_metrics(selected_mva_type, selected_cta_type):
    #Alter campaigns
    # Fetch current user and role from Snowflake
    def fetch_campaigns():
     df = fetch_data_from_snowflake(campaign_meta_query)
     return sorted(df["CTA_CAMPAIGN"].dropna().unique().tolist())

    # Get current user + role
    def get_snowflake_identity():
        query = "SELECT  CURRENT_ROLE() AS ROLE"
        df = fetch_data_from_snowflake(query)
        return  df.iloc[0]["ROLE"]
    
    # MAIN
    role = get_snowflake_identity()
    
    if role == "ANALYTICS_ROLE":
        alter_campaigns = st.sidebar.checkbox("🔧 Alter Campaigns")
    
        if alter_campaigns:
            st.title("🎯 Alter Campaign Selection")
            st.info("Select campaigns to keep active. Unselected campaigns will be excluded.")
        
            campaign_list = fetch_campaigns()
        
            # Multiselect for included (active) campaigns
            included_campaigns = st.multiselect(" Active Campaigns. Deselect campaigns to exclude.", campaign_list, default=sorted(campaign_list))
        
            # Submit button
            if st.button("Submit"):
                selected_campaigns = {campaign: "✅" if campaign in included_campaigns else "❌"
                                      for campaign in campaign_list}
        
                st.markdown("### 📋 Campaign Selection Summary")
                for camp, status in selected_campaigns.items():
                    st.write(f"{status} {camp}")
        
                # Final filtered list (excluded campaigns)
                excluded_campaigns = [camp for camp in campaign_list if camp not in included_campaigns]
        
                # Format strings for SQL IN clauses
                included_campaigns_cleaned = [camp.strip().replace('"', '').upper() for camp in included_campaigns]
                included_campaigns_str = ",".join(f"'{camp}'" for camp in included_campaigns_cleaned)
        
                excluded_campaigns_cleaned = [camp.strip().replace('"', '').upper() for camp in excluded_campaigns]
                excluded_campaigns_str = ",".join(f"'{camp}'" for camp in excluded_campaigns_cleaned)
        
                try:
                    # Update included campaigns to TRUE
                    if included_campaigns:
                        update_true_query = f"""
                        UPDATE user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
                        SET campaign_dash_status = TRUE
                        WHERE UPPER(TRIM(CTA_CAMPAIGN)) IN ({included_campaigns_str})
                        """
                        run_query(update_true_query)
        
                    # Update excluded campaigns to FALSE
                    if excluded_campaigns:
                        update_false_query = f"""
                        UPDATE user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
                        SET campaign_dash_status = FALSE
                        WHERE UPPER(TRIM(CTA_CAMPAIGN)) IN ({excluded_campaigns_str})
                        """
                        run_query(update_false_query)
        
                    st.success("✅ Campaign status successfully updated.")
        
                    # Verification query
                    verify_query = f"""
                    SELECT CTA_CAMPAIGN, campaign_dash_status
                    FROM user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
                    WHERE UPPER(TRIM(CTA_CAMPAIGN)) IN ({included_campaigns_str}{',' if excluded_campaigns else ''}{excluded_campaigns_str})
                    """
                    df_verify = fetch_data_from_snowflake(verify_query)
                    st.dataframe(df_verify)
        
                except Exception as e:
                    st.error(f"❌ Error updating campaign status: {e}")
       
                # Reset button to make all campaign_dash_status TRUE
            if st.button("🔄 Reset All Campaigns to Active"):
                reset_query = """
                UPDATE user_scratch.x_maggarwal.cta_ltv_all_campaigns_17_nov
                SET campaign_dash_status = TRUE
                """
                try:
                    run_query(reset_query)  # Executes the SQL
                    st.success("✅ All campaigns have been reset to active.")
                    # Optionally clear session state selections too:
                    st.session_state.excluded_campaigns = []
                except Exception as e:
                    st.error(f"❌ Error resetting campaigns: {e}")

        
    
        else:
            st.sidebar.write(" Please make the selections from filters below")
            
    def sidebar_filters(campaign_meta_query, available_baseline_query, available_performance_cohort_query, fetch_data_from_snowflake, query_for_baseline_period_template):
        # Fetch campaign meta data
        table_map = {
            "TAMG": {
                "mva_ltv": "enterprise_data.ltv.vw_mva_ltv",
                "cohort_performance": "enterprise_data.ltv.vw_mva_cohort_performance"
            },
            "TA_ONLY": {
                "mva_ltv": "enterprise_data.ltv.vw_mva_ltv_ta_only_revenue",
                "cohort_performance": "enterprise_data.ltv.vw_mva_cohort_performance_ta_only_revenue"
            }
        }
        
        # Use the selected mode to get the appropriate table names
        mva_ltv_table = table_map[selected_mode]["mva_ltv"]
        cohort_performance_table = table_map[selected_mode]["cohort_performance"]
        
        available_baseline_query = available_baseline_query \
                .replace("{mva_ltv}", mva_ltv_table)
                
        query_for_baseline_period_template = query_for_baseline_period_template \
                .replace("{mva_ltv}", mva_ltv_table)
        
        available_performance_cohort_query = available_performance_cohort_query \
                .replace("{cohort_performance}", cohort_performance_table)  
        
        campaign_meta_df = fetch_data_from_snowflake(campaign_meta_query)
    
        # Step 1: Get all unique values
        all_cohorts = sorted(campaign_meta_df["COHORT_DESCRIPTION"].dropna().unique())
        all_campaigns = sorted(campaign_meta_df["CTA_CAMPAIGN"].dropna().unique())
        all_device_groups = sorted(campaign_meta_df["CTA_DEVICE_GROUP"].dropna().unique())
    
        # Step 2: Checkbox to allow cohort-first selection
        use_cohort_first = st.sidebar.checkbox("Select cohort first")
    
        # Initialize selections
        selected_campaigns = []
        selected_cohorts = []
        selected_device_groups = []
    
        if use_cohort_first:
            selected_cohorts = st.sidebar.multiselect("Select Cohort Description(s)", options=all_cohorts, default=[], key="cohort_multiselect")
            filtered_df_by_cohort = campaign_meta_df[campaign_meta_df["COHORT_DESCRIPTION"].isin(selected_cohorts)]
            available_device_groups = sorted(filtered_df_by_cohort["CTA_DEVICE_GROUP"].dropna().unique())
    
            if not available_device_groups:
                st.warning("No device groups found for selected cohorts.")
                st.stop()
    
            selected_device_groups = st.sidebar.selectbox("Select Device Group", options=available_device_groups)
            filtered_campaigns = sorted(
                filtered_df_by_cohort[filtered_df_by_cohort["CTA_DEVICE_GROUP"] == selected_device_groups]["CTA_CAMPAIGN"]
                .dropna().unique()
            )
    
            previous_selected_campaigns = st.session_state.get("campaign_multiselect", [])
            valid_default_campaigns = [c for c in previous_selected_campaigns if c in filtered_campaigns]
            first_default_campaign = filtered_campaigns[0] if filtered_campaigns else None
    
            selected_campaigns = st.sidebar.multiselect(
                "Select Campaign(s)",
                options=filtered_campaigns,
                default=valid_default_campaigns if valid_default_campaigns else ([first_default_campaign] if first_default_campaign else []),
                key="campaign_multiselect"
            )
        else:
            selected_device_groups = st.sidebar.selectbox("Select Device Group", options=all_device_groups)
            filtered_df_by_device = campaign_meta_df[campaign_meta_df["CTA_DEVICE_GROUP"] == selected_device_groups]
            filtered_campaigns = sorted(filtered_df_by_device["CTA_CAMPAIGN"].dropna().unique())
    
            selected_campaigns = st.sidebar.multiselect(
                "Select Campaign(s)", options=filtered_campaigns, default=[], key="campaign_multiselect"
            )
    
            if selected_campaigns:
                filtered_cohorts = sorted(
                    filtered_df_by_device[filtered_df_by_device["CTA_CAMPAIGN"].isin(selected_campaigns)]["COHORT_DESCRIPTION"]
                    .dropna().unique()
                )
                selected_cohorts = st.sidebar.multiselect(
                    "Select Cohort Description(s)", options=filtered_cohorts, default=filtered_cohorts, key="cohort_multiselect"
                )
            else:
                selected_cohorts = []
        st.sidebar.markdown(
            """
            <div style="background-color:#e6f0ff; padding:10px; border-left:5px solid #3399ff; border-radius:5px;">
                <small><i><b>Note:</b> The Monthly View and All Campaign View are independent of this sidebar.</i></small>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Validation
        if use_cohort_first:
            if not selected_cohorts:
                st.warning("Please select at least one Cohort Description to continue.")
                st.stop()
            if not selected_campaigns:
                st.warning("Please select at least one Campaign related to the selected cohort(s).")
                st.stop()
        else:
            if not selected_campaigns:
                st.warning("Please select at least one campaign in the sidebar to continue with the Campaign View, Detail View, and other tabs.")
                st.stop()
            if not selected_cohorts:
                st.warning("Please select at least one Cohort Description related to the selected campaign(s).")
                st.stop()
    
        # Final Filter
        final_filtered_df = campaign_meta_df[
            (campaign_meta_df["COHORT_DESCRIPTION"].isin(selected_cohorts)) &
            (campaign_meta_df["CTA_CAMPAIGN"].isin(selected_campaigns)) &
            (campaign_meta_df["CTA_DEVICE_GROUP"] == selected_device_groups)
        ]
    
        if final_filtered_df.empty:
            st.warning("No matching data found. Please adjust your filters.")
            st.stop()
    
        # Locale Dropdown
        available_locales = sorted(final_filtered_df["CTA_LOCALE"].dropna().unique())
        if not available_locales:
            st.warning("No locales available for the selected cohort, campaign, and device group.")
            st.stop()
    
        selected_locale = st.sidebar.selectbox("Select Locale", options=available_locales)
    
        # Membership Filter
        available_member_type = sorted(final_filtered_df["MEMBERSHIP_COHORT"].dropna().unique())
        default_member_type = ["OVERALL"] if "OVERALL" in available_member_type else available_member_type
    
        selected_member_type = st.sidebar.multiselect(
            "Select Membership types",
            options=available_member_type,
            default=default_member_type
        )
    
        if not selected_member_type:
            st.warning("Please select member_type to continue.")
            st.stop()
    
        # === Format for SQL IN clause ===
        def format_for_sql_in(values):
            cleaned_values = [str(v).strip('"') for v in values]
            return ", ".join(f"'{v}'" for v in cleaned_values)
    
        formatted_cohorts = format_for_sql_in(selected_cohorts)
        formatted_campaigns = format_for_sql_in(selected_campaigns)
        formatted_member_type = format_for_sql_in(selected_member_type)
    
        # === Fetch available baseline periods ===
        available_baseline_df = fetch_data_from_snowflake(available_baseline_query)
        available_baseline_df["VALIDITY_START_DATE"] = pd.to_datetime(available_baseline_df["VALIDITY_START_DATE"]).dt.date
        available_baseline_df["VALIDITY_END_DATE"] = pd.to_datetime(available_baseline_df["VALIDITY_END_DATE"]).dt.date
    
        def format_baseline_period(row):
            return f"{row['VALIDITY_START_DATE'].strftime('%b')}-{row['VALIDITY_END_DATE'].strftime('%b %Y')}"
        available_baseline_df["VALIDITY_PERIOD_LABEL"] = available_baseline_df.apply(format_baseline_period, axis=1)
    
        cohort_validity_periods = []
        for cohort in selected_cohorts:
            cohort_start_date = pd.to_datetime(f"{cohort}-01", format="%b_%Y-%d").date()
            cohort_end_date = cohort_start_date + pd.DateOffset(months=1) - pd.DateOffset(days=1)
            cohort_end_date = cohort_end_date.date()
    
            valid_baseline_periods = available_baseline_df[
                (available_baseline_df["VALIDITY_START_DATE"] <= cohort_end_date) &
                (available_baseline_df["VALIDITY_END_DATE"] >= cohort_start_date)
            ]
            cohort_validity_periods.extend(valid_baseline_periods["VALIDITY_PERIOD_LABEL"].unique())
    
        if not cohort_validity_periods:
            st.warning("No validity period found for the selected cohort(s).")
            st.stop()
    
        selected_validity_label = cohort_validity_periods[0]
        df_filtered = available_baseline_df[available_baseline_df["VALIDITY_PERIOD_LABEL"] == selected_validity_label]
    
        if not df_filtered.empty:
            selected_baseline_desc = df_filtered.iloc[0]["BASE_PERIOD_DESCRIPTION"]
            validity_start_date = df_filtered.iloc[0]["VALIDITY_START_DATE"]
            validity_end_date = df_filtered.iloc[0]["VALIDITY_END_DATE"]
    
            cohort_months = pd.date_range(start=validity_start_date, end=validity_end_date, freq='MS').strftime('%b %Y').tolist()
    
            available_performance_cohort = fetch_data_from_snowflake(available_performance_cohort_query)
            cohort_start_date = available_performance_cohort["COHORT_START_DATE"].dropna().tolist()
            formatted_cohort_start_date = [date.strftime('%b %Y') for date in cohort_start_date]
    
            common_date = list(set(cohort_months) & set(formatted_cohort_start_date))
        else:
            st.sidebar.warning("No baseline period available for the selected description.")
            selected_baseline_desc = ""
            validity_start_date = None
            validity_end_date = None
            cohort_months = []
            common_date = []
    
        # === Final Summary ===
        st.sidebar.info(f"""
        **Selected Filters:**
        - Cohorts: `{", ".join(selected_cohorts)}`
        - Campaigns: `{", ".join(selected_campaigns)}`
        - Locale: `{selected_locale}`
        - Device Group: `{selected_device_groups}`
        - Member Type: `{selected_member_type}`
        - Selected Baseline Period: `{selected_baseline_desc}`
        """)
    
        return {
            "final_filtered_df": final_filtered_df,
            "selected_cohorts": selected_cohorts,
            "selected_campaigns": selected_campaigns,
            "selected_locale": selected_locale,
            "selected_device_groups": selected_device_groups,
            "selected_member_type": selected_member_type,
            "formatted_cohorts": formatted_cohorts,
            "formatted_campaigns": formatted_campaigns,
            "formatted_member_type": formatted_member_type,
            "cohort_months": cohort_months,
            "selected_baseline_desc": selected_baseline_desc,
            "validity_start_date": validity_start_date,
            "validity_end_date": validity_end_date,
            "common_date": common_date,
            "cohort_performance_table": cohort_performance_table,
            "mva_ltv_table": mva_ltv_table
        }
    
            
    # Create Tabs
    tab_monthly_view, tab_all_campaign_view, tab_campaign_view, tab_detailed_view, tab_chart,tab_sql,tab_glossary = create_tabs()

    with tab_monthly_view:
        st.warning("Use the Year and Device dropdowns to filter data for the monthly and channel views.")
        
        selected_cta_name = "'app_download_overall'" if selected_mode == "TAMG" else "'app_download_overall_ta_only'"
    
        monthly_query = monthly_view_query \
            .replace("{group_by_clause}", "TO_CHAR(TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY'), 'YYYY-MM'), TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY')") \
            .replace("{select_channel_column}", "")\
            .replace("{select_cta_name}", selected_cta_name)
    
        channel_query = monthly_view_query \
            .replace("{group_by_clause}", "TO_CHAR(TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY'), 'YYYY-MM'), TO_DATE(COHORT_DESCRIPTION, 'MON_YYYY'), CTA_CHANNEL") \
            .replace("{select_channel_column}", "CTA_CHANNEL, ") \
            .replace("{select_cta_name}", selected_cta_name)
    
        monthly_view_df = fetch_data_from_snowflake(monthly_query)
        channel_view_df = fetch_data_from_snowflake(channel_query)
    
        monthly_view_df['Year'] = monthly_view_df['COHORT'].apply(lambda x: x.split()[1])
        channel_view_df['Year'] = channel_view_df['COHORT'].apply(lambda x: x.split()[1])
    
        cohort_options = ["All Cohorts"] + sorted(monthly_view_df['COHORT'].unique())
    
        col1, col2, col3 = st.columns([2, 1, 2])
    
        with col1:
            selected_years = st.multiselect(
                "Select Year(s):",
                options=sorted(monthly_view_df['Year'].unique()),
                default=sorted(monthly_view_df['Year'].unique())
            )
    
        with col2:
            selected_cohorts = st.multiselect(
                "Select Cohort",
                options=cohort_options,
                default=["All Cohorts"]
            )
    
        # Expand "All Cohorts"
        if "All Cohorts" in selected_cohorts:
            selected_cohorts = sorted(monthly_view_df['COHORT'].unique())
    
        with col3:
            selected_device = st.selectbox(
                "Select Device:",
                options=sorted(monthly_view_df['DEVICE'].unique()),
                index=sorted(monthly_view_df['DEVICE'].unique()).index("Overall") 
                    if "Overall" in monthly_view_df['DEVICE'].unique() else 0
            )
    
        filtered_monthly_df = monthly_view_df[
            (monthly_view_df['Year'].isin(selected_years)) &
            (monthly_view_df['COHORT'].isin(selected_cohorts)) &
            (monthly_view_df['DEVICE'] == selected_device)
        ].drop(columns=['Year'])
    
        st.markdown("### Monthly View")
        if not filtered_monthly_df.empty:
            st.markdown(render_table_with_colors(filtered_monthly_df), unsafe_allow_html=True)
        else:
            st.markdown("_No data available for this year._")
    
        channel_col1, channel_col2, channel_col3 = st.columns([2, 1, 2])
    
        with channel_col1:
            filtered_channels_by_device = channel_view_df[channel_view_df['DEVICE'] == selected_device]
            channel_options = sorted(filtered_channels_by_device['CTA_CHANNEL'].unique())
            default_channel = "googleadwords_int" if "googleadwords_int" in channel_options else (
                channel_options[0] if channel_options else None
            )
    
            selected_channels = st.multiselect(
                "Select Channel(s):",
                options=channel_options,
                default=[default_channel] if default_channel else []
            )
    
        filtered_channel_df = channel_view_df[
            (channel_view_df['Year'].isin(selected_years)) &
            (channel_view_df['COHORT'].isin(selected_cohorts)) &
            (channel_view_df['CTA_CHANNEL'].isin(selected_channels)) &
            (channel_view_df['DEVICE'] == selected_device)
        ].drop(columns=['Year'])
    
        st.markdown("### Channel View")
    
        for channel in selected_channels:
            st.markdown(f"#### 📡 Channel: `{channel}`")
            channel_specific_df = filtered_channel_df[filtered_channel_df['CTA_CHANNEL'] == channel].copy()
            channel_specific_df.drop(columns=["CTA_CHANNEL"], errors='ignore', inplace=True)
    
            if not channel_specific_df.empty:
                st.markdown(render_table_with_colors(channel_specific_df), unsafe_allow_html=True)
            else:
                st.markdown("_No data available for this channel._")

    with tab_all_campaign_view:
        st.warning("Use the Select Channel dropdowns to filter data for the All Campaign view.")
            
        st.title("All Campaign Data")
    
        selected_cta_name = "'app_download_overall'" if selected_mode == "TAMG" else "'app_download_overall_ta_only'"
        all_campaign_query = all_campaign_query_template.replace("{select_cta_name}", selected_cta_name)
        all_campaign_query_df = fetch_data_from_snowflake(all_campaign_query)
    
        # Dropdown options
        actual_channels = sorted(all_campaign_query_df['CTA_CHANNEL'].unique())
        channel_options = ['All Channels'] + actual_channels
    
        cohort_list = sorted(all_campaign_query_df['COHORT'].unique())
        cohort_options = ['All Cohorts'] + cohort_list
    
        # Channel + Cohort filters side-by-side
        col1, col2 = st.columns([2, 2])
    
        with col1:
            selected_channel = st.selectbox(
                "Select Channel",
                options=channel_options,
                index=0
            )
    
        with col2:
            selected_cohorts = st.multiselect(
                "Select Cohort",
                options=cohort_options,
                default=['All Cohorts']
            )
    
        # Apply channel filter first
        if selected_channel == "All Channels":
            filtered_df = all_campaign_query_df.copy()
        else:
            filtered_df = all_campaign_query_df[
                all_campaign_query_df["CTA_CHANNEL"] == selected_channel
            ].copy()
    
        # Apply cohort filter next
        if "All Cohorts" not in selected_cohorts:
            filtered_df = filtered_df[
                filtered_df["COHORT"].isin(selected_cohorts)
            ].copy()
    
        # Remaining campaigns
        filtered_campaigns = filtered_df["CAMPAIGN"].unique()
    
        for campaign in filtered_campaigns:
            campaign_df = filtered_df[filtered_df["CAMPAIGN"] == campaign].copy()
            if campaign_df.empty:
                continue
    
            st.markdown(f"## 🎯 Campaign: `{campaign}`")
    
            campaign_df.drop(columns=["CAMPAIGN", "ON_TRACK_STATUS"], errors="ignore", inplace=True)
    
            st.markdown("### ✅ Tracking Status")
            st.markdown(render_table_with_colors(campaign_df), unsafe_allow_html=True)
                
        
    
    
    with tab_campaign_view:
        filters = sidebar_filters(campaign_meta_query, available_baseline_query, available_performance_cohort_query, fetch_data_from_snowflake, query_for_baseline_period_template)
        final_filtered_df = filters["final_filtered_df"]
        selected_cohorts = filters["selected_cohorts"]
        selected_campaigns = filters["selected_campaigns"]
        selected_locale = filters["selected_locale"]
        selected_device_groups = filters["selected_device_groups"]
        selected_member_type = filters["selected_member_type"]
        formatted_cohorts = filters["formatted_cohorts"]
        formatted_campaigns = filters["formatted_campaigns"]
        formatted_member_type = filters["formatted_member_type"]
        cohort_months = filters["cohort_months"]
        selected_baseline_desc = filters["selected_baseline_desc"]
        validity_start_date = filters["validity_start_date"]
        validity_end_date = filters["validity_end_date"]
        mva_ltv_table = filters["mva_ltv_table"]
        cohort_performance_table = filters["cohort_performance_table"]
        
        # Main queries
        on_track_query = on_track_query_template.format(
            cohorts=formatted_cohorts,
            locale=selected_locale,
            campaigns=formatted_campaigns,
            device_groups=selected_device_groups,
            member_type=formatted_member_type,
            selected_cta_type=selected_cta_type
                
        )
        
        flow_query = flow_query_template.format(
            cohorts=formatted_cohorts,
            locale=selected_locale,
            campaigns=formatted_campaigns,
            device_groups=selected_device_groups,
            member_type=formatted_member_type,
            selected_cta_type=selected_cta_type
        
        )
        
        st.markdown(
            """
            <div style='font-size: 14px;'>
                <a href="https://docs.google.com/document/d/17B4MgiYpcPvO9k8pCvJF4xITff03cQ874MeU14ZBZV4/edit?tab=t.0#heading=h.jxzynz60racj" target="_blank" style="text-decoration: none;">
                    📄 App Campaign LTV Cohort Tracking
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.title("Cohort LTV Tracking Data")
        
        # Fetch data just once for all selected filters
        ontrack_df = fetch_data_from_snowflake(on_track_query)
        
        # Loop over selected campaigns and render two tables per campaign
        for campaign in selected_campaigns:
            st.markdown(f"## 🎯 Campaign: `{campaign}`")
        
            # Filter data for the current campaign and member type = OVERALL        
            campaign_ontrack_df = ontrack_df[
                (ontrack_df["CAMPAIGN"] == campaign)].copy()
            
            # Drop the CAMPAIGN column since it's in the heading
            campaign_ontrack_df.drop(columns=["CAMPAIGN","ON_TRACK_STATUS"], errors='ignore', inplace=True)
        
            # Render On Track Table
            st.markdown("### ✅ Tracking Status")
            if not campaign_ontrack_df.empty:
                st.markdown(render_table_with_colors(campaign_ontrack_df), unsafe_allow_html=True)
            else:
                st.markdown(f"_No data available for **{campaign}** in **{selected_locale}**. Try selecting other locales to view data._")

          
    with tab_detailed_view:
       active_users_query = active_users_query_template.format(
            cohorts=formatted_cohorts,
            locale=selected_locale,
            campaigns=formatted_campaigns,
            device_groups=selected_device_groups,
            member_type=formatted_member_type,
            selected_cta_type=selected_cta_type
    
        )
       active_df = fetch_data_from_snowflake(active_users_query)

       # Normalize column names to handle casing inconsistencies
       active_df.columns = [col.strip().upper() for col in active_df.columns] 
       
        
       # Convert DEVICES_COUNT, USERS_COUNT, QUALIFIED_NEW_INSTALLS to whole numbers (integers)
       for col in ["DEVICES_COUNT", "USERS_COUNT", "QUALIFIED_NEW_INSTALLS"]:
        if col in active_df.columns:
            # st.text(active_df[col])
            active_df[col] = pd.to_numeric(active_df[col], errors='coerce').astype('Int64')
                
       # Format ACTIVE_USERS_PERCENT column if it exists
       flow_df = fetch_data_from_snowflake(flow_query)
       campaign_flow_df = flow_df[
            (flow_df["CAMPAIGN"] == campaign)].copy()
       campaign_flow_df.drop(columns=["CAMPAIGN"], errors='ignore', inplace=True)

       if "ACTIVE_USERS_PERCENT" in active_df.columns:
            active_df["ACTIVE_USERS_PERCENT"] = active_df["ACTIVE_USERS_PERCENT"].apply(
                lambda x: f"{round(float(x), 2)}%" if pd.notnull(x) and isinstance(x, (int, float)) else x
            )
        
       if "REINSTALL_PERCENT" in active_df.columns:
           active_df["REINSTALL_PERCENT"] = active_df["REINSTALL_PERCENT"].apply(
               lambda x: f"{round(float(x), 2)}%" if pd.notnull(x) and isinstance(x, (int, float)) else x
           )
      
       # campaigns_in_active = set(active_df["CAMPAIGN"].unique()) if "CAMPAIGN" in active_df.columns else set()
       # campaigns_in_flow = set(flow_df["CAMPAIGN"].unique()) if "CAMPAIGN" in flow_df.columns else set() 
       # all_unique_campaigns = sorted(campaigns_in_active.union(campaigns_in_flow))

       for campaign in selected_campaigns:
            st.markdown(f"## 📊 User Metrics - Campaign: `{campaign}`")
        
            campaign_df = active_df[active_df["CAMPAIGN"] == campaign].copy() if "CAMPAIGN" in active_df.columns else pd.DataFrame()
            campaign_df.drop(columns=["CAMPAIGN"], inplace=True, errors='ignore')
        
            if not campaign_df.empty:
                st.markdown(render_table_with_colors(campaign_df), unsafe_allow_html=True)
            else:
                st.markdown(f"_No data available for **{campaign}** in **{selected_locale}**. Try selecting other locales._")
        
            st.markdown("---")
        
        # Repeat similarly for Flow:
        
       for campaign in selected_campaigns:
            st.markdown(f"## 🔄 Flow - Campaign: `{campaign}`")
        
            campaign_flow_df = flow_df[flow_df["CAMPAIGN"] == campaign].copy() if "CAMPAIGN" in flow_df.columns else pd.DataFrame()
            campaign_flow_df.drop(columns=["CAMPAIGN"], inplace=True, errors='ignore')
        
            if not campaign_flow_df.empty:
                st.markdown(render_table_with_colors(campaign_flow_df), unsafe_allow_html=True)
            else:
                st.markdown(f"_No data available for **{campaign}** in **{selected_locale}**. Try selecting other locales._")
        
            st.markdown("---")
               
       # st.markdown("---")  
       st.text(f'The chart shows the Profit realization curve for {selected_campaigns} - Campaigns')

       cohort_start_dates = [pd.to_datetime(cohort, format="%b_%Y").replace(day=1).date() for cohort in selected_cohorts]
       cohort_end_dates = [(pd.to_datetime(cohort, format="%b_%Y") + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date() for cohort in selected_cohorts]
          
       query_for_performance_period = []
       for start, end in zip(cohort_start_dates, cohort_end_dates):
             realization_query = realization_query_template.format(
                 cohort_start_date=start,
                 cohort_end_date=end,
                 cohorts=formatted_cohorts,
                 campaigns=formatted_campaigns,
                 locale=selected_locale,
                 device_groups=selected_device_groups,
                 member_type=formatted_member_type,
                 selected_cta_type = selected_cta_type
             )
             query_for_performance_period.append(realization_query)
        
       performance_cohort_df = []
       for query in query_for_performance_period:
              for member_type in selected_member_type:
               df = fetch_data_from_snowflake(query)
               performance_cohort_df.append(df)
      
       if not any(not df.empty for df in performance_cohort_df):
              st.warning(f"No data available for selected locale `{selected_locale}` and device groups `{selected_device_groups}`.")
       else:
              performance_period_columns = [
                  'LTV_15D', 'LTV_30D', 'LTV_45D', 'LTV_60D', 'LTV_03M', 'LTV_04M',
                  'LTV_05M', 'LTV_06M', 'LTV_07M', 'LTV_08M', 'LTV_09M', 'LTV_10M', 'LTV_11M', 'LTV_12M'
              ]
              performance_period_labels = [
                  '15D', '30D', '45D', '60D', '03M', '04M', '05M',
                  '06M', '07M', '08M', '09M', '10M', '11M', '12M'
              ]
              performance_status_columns = [col + '_BASIS' for col in performance_period_columns]
              performance_period_labels = [label[4:] for label in performance_period_columns]
              # New: Custom mapping for axis spacing
              period_label_to_day = {
                  '15D': 15, '30D': 30, '45D': 45, '60D': 60,
                  '03M': 90, '04M': 120, '05M': 150, '06M': 180,
                  '07M': 210, '08M': 240, '09M': 270, '10M': 300, '11M': 330, '12M': 360
              }
       
              fig = go.Figure()
              colors = ['#ea4335', '#fbbc05','#34a853', '#ff9900', '#ff6600', '#33cc33', '#0066cc', '#9900cc', '#cc6699', '#ff3399',  
                        '#6633cc', '#00bfae', '#999900', '#ff6666', '#3399ff', '#cc3300', '#003366', '#990099', '#66ccff', '#228b22',
                        '#ffb347', '#a83279', '#5dade2', '#af7ac5', '#48c9b0', '#f1948a', '#7fb3d5', '#f7dc6f', '#85929e', '#dc7633' 
                       ]
       
     
              # Add campaign curves with tooltips using LTV_12M
              for c_idx, campaign in enumerate(selected_campaigns):
                   for cohort_name, df in zip(selected_cohorts, performance_cohort_df):
                       for member_type in selected_member_type:
                           if not df.empty:
                               filtered_df = df[
                                   (df["CTA_CAMPAIGN"] == campaign) &
                                   (df["COHORT_DESCRIPTION"] == cohort_name) &
                                   (df["MEMBERSHIP_COHORT"] == member_type)
                               ]
               
                               if not filtered_df.empty:
                                   row = filtered_df.iloc[0]
               
                                   observed_x, observed_y, observed_tooltips = [], [], []
                                   extrapolated_x, extrapolated_y, extrapolated_tooltips = [], [], []
               
                                   ltv_12m = row.get("LTV_12M", None)
               
                                   for i, col in enumerate(performance_period_columns):
                                       value = row[col]
                                       status = row[performance_status_columns[i]]
                                       label = performance_period_labels[i]
                                       day_value = period_label_to_day[label]
               
                                       if value is not None and ltv_12m not in (None, 0):
                                           realization = (value / ltv_12m) * 100
                                           tooltip = f"{label}: ${value:.2f} ({realization:.2f}%)"
                                       else:
                                           tooltip = f"{label}: N/A"
               
                                       if status == "OBSERVED":
                                           observed_x.append(day_value)
                                           observed_y.append(value)
                                           observed_tooltips.append(tooltip)
                                       elif status == "EXTRAPOLATED":
                                           extrapolated_x.append(day_value)
                                           extrapolated_y.append(value)
                                           extrapolated_tooltips.append(tooltip)
               
                                   color_index = (c_idx * 3 + hash(cohort_name + member_type) % 100) % len(colors)
                                   line_color = colors[color_index]
               
                                   if observed_x and observed_y:
                                       fig.add_trace(go.Scatter(
                                           x=observed_x,
                                           y=observed_y,
                                           mode='lines+markers+text',
                                           name=f"{campaign} <br> {cohort_name} ({member_type}) (Observed)",
                                           line=dict(color=line_color, width=2),
                                           marker=dict(size=6),
                                           text=[f"${format_number(v)}" for v in observed_y],
                                           textposition="top center",
                                           hovertext=observed_tooltips,
                                           hoverinfo='text'
                                       ))
                                   has_negative_observed = any(y < 0 for y in observed_y)
                                   if extrapolated_x:
                                       if extrapolated_y:
                                           if has_negative_observed:
                                               # Replace y values with None so x-axis still renders
                                               extrapolated_y = [None for _ in extrapolated_y]
                                               text_vals = [""] * len(extrapolated_y)
                                               hover_vals = [""] * len(extrapolated_y)
                                           else:
                                               if observed_x and observed_y:
                                                   extrapolated_x.insert(0, observed_x[-1])
                                                   extrapolated_y.insert(0, observed_y[-1])
                                                   extrapolated_tooltips.insert(0, observed_tooltips[-1])
                                               
                                               text_vals = [f"${format_number(v)}" for v in extrapolated_y]
                                               hover_vals = extrapolated_tooltips
                                    
                                           fig.add_trace(go.Scatter(
                                               x=extrapolated_x,
                                               y=extrapolated_y,
                                               mode='lines+markers+text',
                                               name=f"{campaign} <br> {cohort_name} ({member_type}) (Extrapolated)",
                                               line=dict(color=line_color, dash='dash', width=2),
                                               marker=dict(size=6),
                                               text=text_vals,
                                               textposition="top center",
                                               hovertext=hover_vals,
                                               hoverinfo='text'
                                           ))
        
              fig.update_layout(
                  title=f"Profit Realization Curve – {selected_locale} | {selected_device_groups}",
                  xaxis=dict(
                      title="Profit Period",
                      tickmode="array",
                      tickvals=list(period_label_to_day.values()),
                      ticktext=list(period_label_to_day.keys()),
                      showgrid=False
                  ),
                  yaxis=dict(title="Profit ($)", tickprefix="$", showgrid=True),
                  plot_bgcolor="white",
                  legend_title="Campaign – Cohort – Device",
                  showlegend=True,
                  height=500,
                  margin=dict(t=50, l=50, r=40, b=50)
              )
  
              st.plotly_chart(fig, use_container_width=True)

    
    with tab_chart:
        st.text(f'The chart shows the LTV realization curve for {selected_campaigns} - Campaigns')
        
        # Date parsing for cohorts
        cohort_start_dates = [pd.to_datetime(cohort, format="%b_%Y").replace(day=1).date() for cohort in selected_cohorts]
        cohort_end_dates = [(pd.to_datetime(cohort, format="%b_%Y") + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date() for cohort in selected_cohorts]
       
        # Constructing the queries for performance period
        query_for_performance_period = []
        for start, end in zip(cohort_start_dates, cohort_end_dates):
            realization_query = realization_ltv_query_template.format(
                cohort_start_date=start,
                cohort_end_date=end,
                cohorts=formatted_cohorts,
                campaigns=formatted_campaigns,
                locale=selected_locale,
                device_groups=selected_device_groups,
                member_type=formatted_member_type,
                selected_cta_type=selected_cta_type
            )
            query_for_performance_period.append(realization_query)
    
        performance_cohort_df = []
        # Fetching and processing data for each query
        for query in query_for_performance_period:
            df = fetch_data_from_snowflake(query)
            performance_cohort_df.append(df)
    
        if not any(not df.empty for df in performance_cohort_df):
            st.warning(f"No data available for selected locale `{selected_locale}` and device groups `{selected_device_groups}`.")
        else:
            # Define periods and date mapping
            performance_period_columns = [
                'LTV_15D', 'LTV_30D', 'LTV_45D', 'LTV_60D', 'LTV_03M', 'LTV_04M',
                'LTV_05M', 'LTV_06M', 'LTV_07M', 'LTV_08M', 'LTV_09M', 'LTV_10M', 'LTV_11M', 'LTV_12M'
            ]
            performance_status_columns = [col + '_BASIS' for col in performance_period_columns]
            performance_period_labels = [label[4:] for label in performance_period_columns]  # '15D', '30D', etc.
            period_label_to_day = {
                '15D': 15, '30D': 30, '45D': 45, '60D': 60,
                '03M': 90, '04M': 120, '05M': 150, '06M': 180,
                '07M': 210, '08M': 240, '09M': 270, '10M': 300,
                '11M': 330, '12M': 360
            }
    
            # Color palette for the chart
            colors = ['#ea4335', '#fbbc05','#34a853', '#ff9900', '#ff6600', '#33cc33', '#0066cc', '#9900cc', '#cc6699', '#ff3399',  
                     '#6633cc', '#00bfae', '#999900', '#ff6666', '#3399ff', '#cc3300', '#003366', '#990099', '#66ccff', '#228b22',
                     '#ffb347', '#a83279', '#5dade2', '#af7ac5', '#48c9b0', '#f1948a', '#7fb3d5', '#f7dc6f', '#85929e', '#dc7633' 
                    ]
            
            fig = go.Figure()
    
            # Add baseline if available
            query_for_baseline_period = query_for_baseline_period_template.format(mva_ltv=mva_ltv_table,selected_baseline_desc=selected_baseline_desc, locale=selected_locale, device_groups=selected_device_groups,selected_mva_type=selected_mva_type)
            baseline_df = fetch_data_from_snowflake(query_for_baseline_period)
            
            filtered_baseline = baseline_df[
                (baseline_df['MVA_LOCALE'] == selected_locale) &
                (baseline_df['MVA_DEVICE_GROUP']== selected_device_groups) 
            ]
            
            if filtered_baseline.empty:
                st.warning(f"No baseline data available for {selected_locale} and {selected_device_groups}")
            else:
                row = filtered_baseline.iloc[0]
                baseline_values = [round(row[f"LTV_BASELINE_{label}"], 2) for label in performance_period_labels]
                baseline_dates = [period_label_to_day[label] for label in performance_period_labels]
                # tooltips = [f"{label}: ${val:.2f}" for label, val in zip(performance_period_labels, baseline_values)]

                tooltips = []
                ltv_12m = row.get("LTV_BASELINE_12M", None)
                
                for label in performance_period_labels:
                    col = f"LTV_BASELINE_{label}"
                    ltv_val = row.get(col, None)
                
                    if ltv_val is not None and ltv_12m not in (None, 0):
                        realization = (ltv_val / ltv_12m) * 100
                        tooltips.append(f"{label}: ${ltv_val:.2f} ({realization:.2f}%)")
                    else:
                        tooltips.append(f"{label}: N/A")
                                
                fig.add_trace(go.Scatter(
                    x=baseline_dates,
                    y=baseline_values,
                    mode='lines+markers+text',
                    name="Baseline",
                    text=[f"${val:.2f}" for val in baseline_values],
                    textposition="top center",
                    line=dict(color='blue', width=2),
                    marker=dict(size=6),
                    hovertext=tooltips,
                    hoverinfo='text'
                ))
    

            # Add campaign curves for each member type
            for c_idx, campaign in enumerate(selected_campaigns):
                for cohort_name, df in zip(selected_cohorts, performance_cohort_df):
                    for member_type in selected_member_type:
                        if not df.empty:
                            filtered_df = df[
                                (df["CTA_CAMPAIGN"] == campaign) &
                                (df["COHORT_DESCRIPTION"] == cohort_name) &
                                (df["MEMBERSHIP_COHORT"] == member_type)
                            ]
                            if not filtered_df.empty:
                                row = filtered_df.iloc[0]
                                observed_x, observed_y, observed_tooltips = [], [], []
                                extrapolated_x, extrapolated_y, extrapolated_tooltips = [], [], []
            
                                ltv_12m = row.get("LTV_12M", None)
            
                                for i, col in enumerate(performance_period_columns):
                                    value = row[col]
                                    status = row[performance_status_columns[i]]
                                    label = performance_period_labels[i]
                                    day_value = period_label_to_day[label]
            
                                    # Create realization tooltip based on LTV_12M
                                    if value is not None and ltv_12m not in (None, 0):
                                        realization = (value / ltv_12m) * 100
                                        tooltip = f"{label}: ${value:.2f} ({realization:.2f}%)"
                                    else:
                                        tooltip = f"{label}: N/A"
            
                                    if status == "OBSERVED":
                                        observed_x.append(day_value)
                                        observed_y.append(value)
                                        observed_tooltips.append(tooltip)
                                    elif status == "EXTRAPOLATED":
                                        extrapolated_x.append(day_value)
                                        extrapolated_y.append(value)
                                        extrapolated_tooltips.append(tooltip)
            
                                color_index = (c_idx * len(selected_device_groups) + hash(cohort_name + member_type) % 100) % len(colors)
                                line_color = colors[color_index]
            
                                if observed_x:
                                    fig.add_trace(go.Scatter(
                                        x=observed_x,
                                        y=observed_y,
                                        mode='lines+markers+text',
                                        name=f"{campaign} <br> {cohort_name} ({member_type}) – Obs",
                                        line=dict(color=line_color, width=2),
                                        marker=dict(size=6),
                                        text=[f"${v:.2f}" for v in observed_y],
                                        textposition="top center",
                                        hovertext=observed_tooltips,
                                        hoverinfo='text'
                                    ))

                                has_negative_observed = any(y < 0 for y in observed_y)
                                if extrapolated_x and not has_negative_observed:
                                    if observed_x:
                                        extrapolated_x.insert(0, observed_x[-1])
                                        extrapolated_y.insert(0, observed_y[-1])
                                        extrapolated_tooltips.insert(0, observed_tooltips[-1])
            
                                    fig.add_trace(go.Scatter(
                                        x=extrapolated_x,
                                        y=extrapolated_y,
                                        mode='lines+markers+text',
                                        name=f"{campaign} <br> {cohort_name} ({member_type}) – Extra",
                                        line=dict(color=line_color, dash='dash', width=2),
                                        marker=dict(size=6),
                                        text=[f"${v:.2f}" for v in extrapolated_y],
                                        textposition="top center",
                                        hovertext=extrapolated_tooltips,
                                        hoverinfo='text'
                                    ))
    
            # Final layout setup for the chart
            fig.update_layout(
                title=f"LTV Realization Curve – {selected_locale} | {selected_device_groups}",
                xaxis=dict(
                    title="LTV Period",
                    tickmode="array",
                    tickvals=list(period_label_to_day.values()),
                    ticktext=list(period_label_to_day.keys()),
                    showgrid=False
                ),
                yaxis=dict(title="LTV Value($)", tickprefix="$", showgrid=True),
                plot_bgcolor="white",
                legend_title="Campaign – Cohort – Device - Member type",
                showlegend=True,
                height=550,
                margin=dict(t=50, l=50, r=40, b=50)
            )
    
            st.plotly_chart(fig, use_container_width=True)    


    with tab_sql:
           st.title("Campaign Cohort SQL Queries")
           show_sql_code({
                "Monthly View " : monthly_query,
                "Channel View" : channel_query,
                "On Track Query": on_track_query,
                "Flow Query": flow_query,
                "Active Users Query": active_users_query
            })
    with tab_glossary:
        st.title("Campaign Cohort SQL Queries")
        st.title("Data Description")
        
        glossary_df = fetch_data_from_snowflake(glossary_query_template)
        st.markdown(render_table_with_colors(glossary_df), unsafe_allow_html=True)
        
                 
#---------------------------------------------------------------

# def show_radio_button_for_selection():
    # Map page names to their corresponding bounty types
page_names_to_bounty_types = {
        "📱 App Download": "app_download",
    #   "🧑‍🤝‍🧑 Member": "member_registration",
    #   "✈️ Trips": "trip_creation"  
    }
    
is_tamg = st.toggle("Show TA Only View", value=False)  # Default: TAMG

selected_mode = "TA_ONLY" if is_tamg else "TAMG"
selected_radio_button = st.radio("Select the MVA", list(page_names_to_bounty_types.keys())) 
if selected_mode == "TAMG":
    st.markdown("""
        <div style='font-size: 0.85rem; color: #3c3c3c; background-color: #eaf4fc; border-left: 6px solid #2196F3; padding: 0.5em 1em; border-radius: 5px;'>
          <strong>👀 This data includes Viator revenue!</strong><br>
          ⚠️ The iOS SKAN campaigns are calculated based on approximate value.<br>
          📉 Non-member LTV is estimated as one-tenth of Member LTV.
        </div>
        """, unsafe_allow_html=True)


    selected_cta_type = "'app_download','app_download_nm','app_download_overall'"
else:
    st.markdown("""
        <div style='font-size: 0.85rem; color: #3c3c3c; background-color: #eaf4fc; border-left: 6px solid #2196F3; padding: 0.5em 1em; border-radius: 5px;'>
          <strong>👀 This data includes Viator revenue!</strong><br>
          ⚠️ The iOS SKAN campaigns are calculated based on approximate value.<br>
          📉 Non-member LTV is estimated as one-tenth of Member LTV.
        </div>
        """, unsafe_allow_html=True)
    selected_cta_type = "'app_download_ta_only','app_download_nm_ta_only','app_download_overall_ta_only'"
     
    
    # Get the corresponding bounty type
selected_mva_type = page_names_to_bounty_types[selected_radio_button or "📱 App"]

show_bounty_metrics(selected_mva_type, selected_cta_type)
     # show_bounty_metrics(selected_cta_type if not is_tamg else selected_cta_type+"_ta_only"   )
     # show_bounty_metrics(selected_mva_type)

# show_radio_button_for_selection()
