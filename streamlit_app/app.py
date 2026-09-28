import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import time
import re

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fitness Analytics Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "cleaned_data" / "fitness_analytics.duckdb"

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.4rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }

        .section-title {
            font-size: 1.4rem;
            font-weight: 650;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }

        div[data-testid="stMetric"] {
            padding: 10px;
            border-radius: 10px;
        }

        .small-note {
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


con = get_connection()

# ============================================================
# QUERY FUNCTION
# ============================================================

@st.cache_data(ttl=300)
def run_query(query):
    return con.execute(query).df()


# ============================================================
# DATABASE CHECK
# ============================================================

if not DB_PATH.exists():

    st.error(
        f"Database not found:\n\n{DB_PATH}"
    )

    st.stop()


# ============================================================
# TABLE INFORMATION
# ============================================================

TABLES = [
    "daily_activity",
    "hourly_activity",
    "sleep_daily",
    "activity_sleep"
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def safe_query(query):
    try:
        return con.execute(query).df()
    except Exception as e:
        return None


def sql_is_safe(query):
    """
    Allows read-only analytical SQL for the playground.
    Blocks destructive/database-modifying commands.
    """

    cleaned = re.sub(
        r"--.*?$|/\*.*?\*/",
        "",
        query,
        flags=re.MULTILINE | re.DOTALL
    ).strip()

    if not cleaned:
        return False, "Please enter a SQL query."

    # Remove trailing semicolons for validation
    normalized = cleaned.rstrip(";").strip()

    # Only allow SELECT / WITH
    if not re.match(r"^(SELECT|WITH)\b", normalized, re.IGNORECASE):
        return False, "Only SELECT and WITH queries are allowed."

    blocked = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "ATTACH",
        "DETACH",
        "COPY",
        "EXPORT",
        "IMPORT",
        "INSTALL",
        "LOAD",
        "CALL",
        "SET",
        "RESET"
    ]

    for word in blocked:

        if re.search(
            rf"\b{word}\b",
            normalized,
            flags=re.IGNORECASE
        ):
            return False, f"'{word}' commands are not allowed."

    # Prevent multiple statements
    if ";" in normalized:
        return False, "Only one SQL statement is allowed at a time."

    return True, ""


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🏃 Fitness Analytics")

st.sidebar.caption("Interactive Fitness Data Analytics")

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Executive Overview",
        "📅 Daily Activity",
        "⏰ Hourly Behavior",
        "😴 Sleep & Recovery",
        "👤 User Insights",
        "🧮 SQL Analytics",
        "💻 Live SQL Playground",
        "📋 Data Quality & Methodology"
    ]
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Data source: cleaned fitness tracking dataset"
)

# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "🏠 Executive Overview":

    st.markdown(
        '<div class="main-title">🏃 Fitness Analytics Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        "A comprehensive analysis of daily activity, hourly behavior, "
        "sleep patterns and user-level fitness behavior."
    )

    # --------------------------------------------------------
    # KPI DATA
    # --------------------------------------------------------

    kpi = run_query(
        """
        SELECT
            COUNT(DISTINCT id) AS users,
            COUNT(*) AS records,
            ROUND(AVG(total_steps), 2) AS avg_steps,
            ROUND(AVG(calories), 2) AS avg_calories,
            ROUND(AVG(total_active_minutes), 2)
                AS avg_active_minutes,
            ROUND(AVG(sedentary_minutes), 2)
                AS avg_sedentary_minutes
        FROM daily_activity
        """
    ).iloc[0]

    sleep_kpi = run_query(
        """
        SELECT
            ROUND(AVG(sleep_hours), 2) AS avg_sleep
        FROM sleep_daily
        """
    ).iloc[0]

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric(
        "Users",
        f"{int(kpi['users'])}"
    )

    c2.metric(
        "Activity Records",
        f"{int(kpi['records']):,}"
    )

    c3.metric(
        "Avg Steps",
        format_number(kpi["avg_steps"])
    )

    c4.metric(
        "Avg Calories",
        format_number(kpi["avg_calories"])
    )

    c5.metric(
        "Avg Active Minutes",
        f"{kpi['avg_active_minutes']:.1f}"
    )

    c6.metric(
        "Avg Sleep",
        f"{sleep_kpi['avg_sleep']:.2f} hrs"
    )

    st.markdown("---")

    # --------------------------------------------------------
    # DAILY TREND
    # --------------------------------------------------------

    st.subheader("📈 Daily Activity Trend")

    trend = run_query(
        """
        SELECT
            activity_date,
            ROUND(AVG(total_steps), 2) AS avg_steps,
            ROUND(AVG(calories), 2) AS avg_calories
        FROM daily_activity
        GROUP BY activity_date
        ORDER BY activity_date
        """
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=trend["activity_date"],
            y=trend["avg_steps"],
            mode="lines+markers",
            name="Average Steps"
        )
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Average Steps",
        height=420,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------------
    # DAY TYPE
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("📅 Weekday vs Weekend")

        day_type = run_query(
            """
            SELECT
                day_type,
                ROUND(AVG(total_steps), 2) AS avg_steps,
                ROUND(AVG(calories), 2) AS avg_calories,
                ROUND(AVG(total_active_minutes), 2)
                    AS avg_active_minutes,
                ROUND(AVG(sedentary_minutes), 2)
                    AS avg_sedentary_minutes
            FROM daily_activity
            GROUP BY day_type
            """
        )

        st.dataframe(
            day_type,
            use_container_width=True,
            hide_index=True
        )

    with col2:

        st.subheader("😴 Sleep Summary")

        sleep_summary = run_query(
            """
            SELECT
                COUNT(*) AS records,
                COUNT(DISTINCT id) AS users,
                ROUND(AVG(sleep_hours), 2)
                    AS avg_sleep_hours,
                ROUND(MEDIAN(sleep_hours), 2)
                    AS median_sleep_hours,
                ROUND(AVG(time_in_bed_hours), 2)
                    AS avg_time_in_bed
            FROM sleep_daily
            """
        )

        st.dataframe(
            sleep_summary,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# DAILY ACTIVITY
# ============================================================

elif page == "📅 Daily Activity":

    st.markdown(
        '<div class="main-title">📅 Daily Activity Analysis</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Explore daily movement, calories, active time and sedentary behavior."
    )

    # --------------------------------------------------------
    # DATE RANGE
    # --------------------------------------------------------

    dates = run_query(
        """
        SELECT
            MIN(activity_date) AS min_date,
            MAX(activity_date) AS max_date
        FROM daily_activity
        """
    ).iloc[0]

    selected_dates = st.date_input(
        "Select date range",
        value=(
            dates["min_date"].date(),
            dates["max_date"].date()
        )
    )

    if len(selected_dates) != 2:

        st.warning("Please select a start and end date.")

        st.stop()

    start_date = selected_dates[0]
    end_date = selected_dates[1]

    daily = run_query(
        f"""
        SELECT *
        FROM daily_activity
        WHERE activity_date
            BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY activity_date
        """
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Average Steps",
        f"{daily['total_steps'].mean():,.0f}"
    )

    c2.metric(
        "Average Calories",
        f"{daily['calories'].mean():,.0f}"
    )

    c3.metric(
        "Active Minutes",
        f"{daily['total_active_minutes'].mean():,.1f}"
    )

    c4.metric(
        "Sedentary Minutes",
        f"{daily['sedentary_minutes'].mean():,.1f}"
    )

    st.markdown("---")

    # --------------------------------------------------------
    # STEPS
    # --------------------------------------------------------

    st.subheader("🚶 Average Steps Over Time")

    steps = (
        daily
        .groupby("activity_date")["total_steps"]
        .mean()
        .reset_index()
    )

    fig = px.line(
        steps,
        x="activity_date",
        y="total_steps",
        markers=True
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Average Steps"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------------
    # CALORIES + ACTIVE
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("🔥 Calories")

        calories = (
            daily
            .groupby("activity_date")["calories"]
            .mean()
            .reset_index()
        )

        fig = px.line(
            calories,
            x="activity_date",
            y="calories",
            markers=True
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Average Calories"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.subheader("🏃 Active vs Sedentary")

        activity_time = (
            daily
            .groupby("activity_date")[
                [
                    "total_active_minutes",
                    "sedentary_minutes"
                ]
            ]
            .mean()
            .reset_index()
        )

        fig = px.line(
            activity_time,
            x="activity_date",
            y=[
                "total_active_minutes",
                "sedentary_minutes"
            ],
            markers=True
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Minutes"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # DAY OF WEEK
    # --------------------------------------------------------

    st.subheader("📅 Activity by Day of Week")

    weekday = run_query(
        """
        SELECT
            day_name,
            ROUND(AVG(total_steps), 2) AS avg_steps,
            ROUND(AVG(calories), 2) AS avg_calories,
            ROUND(AVG(total_active_minutes), 2)
                AS avg_active_minutes,
            ROUND(AVG(sedentary_minutes), 2)
                AS avg_sedentary_minutes
        FROM daily_activity
        GROUP BY day_name
        ORDER BY
            CASE day_name
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
        """
    )

    fig = px.bar(
        weekday,
        x="day_name",
        y="avg_steps",
        labels={
            "day_name": "Day",
            "avg_steps": "Average Steps"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.dataframe(
        weekday,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # TOP DAYS
    # --------------------------------------------------------

    st.subheader("🔥 Top Activity Days")

    top_days = run_query(
        """
        SELECT
            activity_date,
            ROUND(AVG(total_steps), 2) AS avg_steps,
            ROUND(AVG(calories), 2) AS avg_calories,
            ROUND(AVG(total_active_minutes), 2)
                AS avg_active_minutes
        FROM daily_activity
        GROUP BY activity_date
        ORDER BY avg_steps DESC
        LIMIT 10
        """
    )

    st.dataframe(
        top_days,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# HOURLY BEHAVIOR
# ============================================================

elif page == "⏰ Hourly Behavior":

    st.markdown(
        '<div class="main-title">⏰ Hourly Behavior</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Analyze activity patterns across the 24-hour day."
    )

    hourly = run_query(
        """
        SELECT
            EXTRACT(HOUR FROM activity_hour) AS hour,
            ROUND(AVG(step_total), 2) AS avg_steps,
            ROUND(AVG(calories), 2) AS avg_calories,
            ROUND(AVG(total_intensity), 2)
                AS avg_total_intensity,
            ROUND(AVG(average_intensity), 3)
                AS avg_intensity
        FROM hourly_activity
        GROUP BY hour
        ORDER BY hour
        """
    )

    # --------------------------------------------------------
    # PEAK HOUR
    # --------------------------------------------------------

    peak = hourly.loc[
        hourly["avg_steps"].idxmax()
    ]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Peak Activity Hour",
        f"{int(peak['hour']):02d}:00"
    )

    c2.metric(
        "Peak Hour Steps",
        f"{peak['avg_steps']:,.0f}"
    )

    c3.metric(
        "Peak Hour Calories",
        f"{peak['avg_calories']:,.1f}"
    )

    st.markdown("---")

    # --------------------------------------------------------
    # 24-HOUR CURVE
    # --------------------------------------------------------

    st.subheader("🕐 24-Hour Activity Curve")

    fig = px.line(
        hourly,
        x="hour",
        y="avg_steps",
        markers=True
    )

    fig.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Average Steps",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------------
    # HOURLY METRICS
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("🚶 Steps by Hour")

        fig = px.bar(
            hourly,
            x="hour",
            y="avg_steps"
        )

        fig.update_layout(
            xaxis_title="Hour",
            yaxis_title="Average Steps"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.subheader("🔥 Calories by Hour")

        fig = px.bar(
            hourly,
            x="hour",
            y="avg_calories"
        )

        fig.update_layout(
            xaxis_title="Hour",
            yaxis_title="Average Calories"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # WEEKDAY VS WEEKEND
    # --------------------------------------------------------

    st.subheader("📊 Weekday vs Weekend — Hourly Pattern")

    hourly_type = run_query(
        """
        SELECT
            CASE
                WHEN EXTRACT(
                    DOW FROM activity_hour
                ) IN (0, 6)
                    THEN 'Weekend'
                ELSE 'Weekday'
            END AS day_type,

            EXTRACT(
                HOUR FROM activity_hour
            ) AS hour,

            ROUND(
                AVG(step_total), 2
            ) AS avg_steps

        FROM hourly_activity

        GROUP BY
            day_type,
            hour

        ORDER BY
            day_type,
            hour
        """
    )

    fig = px.line(
        hourly_type,
        x="hour",
        y="avg_steps",
        color="day_type",
        markers=True
    )

    fig.update_layout(
        xaxis_title="Hour",
        yaxis_title="Average Steps",
        xaxis=dict(dtick=1)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------------
    # HEATMAP
    # --------------------------------------------------------

    st.subheader("🔥 Hour × Day Activity Heatmap")

    heatmap_data = run_query(
        """
        SELECT
            day_name,
            EXTRACT(
                HOUR FROM activity_hour
            ) AS hour,
            ROUND(
                AVG(step_total), 2
            ) AS avg_steps

        FROM (
            SELECT
                *,
                CASE
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 0 THEN 'Sunday'
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 1 THEN 'Monday'
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 2 THEN 'Tuesday'
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 3 THEN 'Wednesday'
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 4 THEN 'Thursday'
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 5 THEN 'Friday'
                    WHEN EXTRACT(
                        DOW FROM activity_hour
                    ) = 6 THEN 'Saturday'
                END AS day_name

            FROM hourly_activity
        )

        GROUP BY
            day_name,
            hour
        """
    )

    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    heatmap_data["day_name"] = pd.Categorical(
        heatmap_data["day_name"],
        categories=day_order,
        ordered=True
    )

    heatmap_data = heatmap_data.sort_values(
        ["day_name", "hour"]
    )

    pivot = heatmap_data.pivot(
        index="day_name",
        columns="hour",
        values="avg_steps"
    )

    fig = px.imshow(
        pivot,
        aspect="auto",
        labels={
            "x": "Hour",
            "y": "Day",
            "color": "Average Steps"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# SLEEP & RECOVERY
# ============================================================

elif page == "😴 Sleep & Recovery":

    st.markdown(
        '<div class="main-title">😴 Sleep & Recovery</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Explore sleep duration, time in bed and relationships with activity."
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    sleep_kpi = run_query(
        """
        SELECT
            COUNT(*) AS records,
            COUNT(DISTINCT id) AS users,
            ROUND(AVG(sleep_hours), 2)
                AS avg_sleep,
            ROUND(MEDIAN(sleep_hours), 2)
                AS median_sleep,
            ROUND(AVG(time_in_bed_hours), 2)
                AS avg_bed
        FROM sleep_daily
        """
    ).iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Sleep Records",
        f"{int(sleep_kpi['records'])}"
    )

    c2.metric(
        "Users",
        f"{int(sleep_kpi['users'])}"
    )

    c3.metric(
        "Avg Sleep",
        f"{sleep_kpi['avg_sleep']:.2f} hrs"
    )

    c4.metric(
        "Median Sleep",
        f"{sleep_kpi['median_sleep']:.2f} hrs"
    )

    c5.metric(
        "Avg Time in Bed",
        f"{sleep_kpi['avg_bed']:.2f} hrs"
    )

    st.markdown("---")

    # --------------------------------------------------------
    # SLEEP BY DAY
    # --------------------------------------------------------

    sleep_day = run_query(
        """
        SELECT
            day_name,
            ROUND(AVG(sleep_hours), 2)
                AS avg_sleep_hours,
            ROUND(AVG(time_in_bed_hours), 2)
                AS avg_time_in_bed
        FROM sleep_daily
        GROUP BY day_name
        ORDER BY
            CASE day_name
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
        """
    )

    st.subheader("📅 Sleep Duration by Day")

    fig = px.bar(
        sleep_day,
        x="day_name",
        y="avg_sleep_hours"
    )

    fig.update_layout(
        xaxis_title="Day",
        yaxis_title="Average Sleep Hours"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------------
    # SLEEP CATEGORIES
    # --------------------------------------------------------

    st.subheader("🛏️ Sleep Duration Categories")

    categories = run_query(
        """
        SELECT
            CASE
                WHEN sleep_hours < 5
                    THEN '<5 hours'

                WHEN sleep_hours < 7
                    THEN '5–7 hours'

                WHEN sleep_hours < 9
                    THEN '7–9 hours'

                ELSE '9+ hours'
            END AS sleep_category,

            COUNT(*) AS records

        FROM sleep_daily

        GROUP BY sleep_category

        ORDER BY
            CASE sleep_category
                WHEN '<5 hours' THEN 1
                WHEN '5–7 hours' THEN 2
                WHEN '7–9 hours' THEN 3
                WHEN '9+ hours' THEN 4
            END
        """
    )

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(
            categories,
            x="sleep_category",
            y="records"
        )

        fig.update_layout(
            xaxis_title="Sleep Category",
            yaxis_title="Records"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.dataframe(
            categories,
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # ACTIVITY + SLEEP
    # --------------------------------------------------------

    st.subheader("🔗 Sleep vs Activity")

    correlation = run_query(
        """
        SELECT
            ROUND(
                CORR(sleep_hours, total_steps),
                3
            ) AS sleep_steps,
            ROUND(
                CORR(sleep_hours, total_active_minutes),
                3
            ) AS sleep_activity,
            ROUND(
                CORR(sleep_hours, sedentary_minutes),
                3
            ) AS sleep_sedentary
        FROM activity_sleep
        """
    )

    st.dataframe(
        correlation,
        use_container_width=True,
        hide_index=True
    )

    scatter = run_query(
        """
        SELECT
            sleep_hours,
            total_steps,
            sedentary_minutes,
            total_active_minutes
        FROM activity_sleep
        """
    )

    fig = px.scatter(
        scatter,
        x="sleep_hours",
        y="total_steps",
        trendline="ols",
        labels={
            "sleep_hours": "Sleep Hours",
            "total_steps": "Total Steps"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# USER INSIGHTS
# ============================================================

elif page == "👤 User Insights":

    st.markdown(
        '<div class="main-title">👤 User Insights</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Explore user-level activity, sleep and data coverage."
    )

    users = run_query(
        """
        SELECT
            id,
            COUNT(*) AS activity_days,
            ROUND(AVG(total_steps), 2)
                AS avg_steps,
            ROUND(AVG(calories), 2)
                AS avg_calories,
            ROUND(AVG(total_active_minutes), 2)
                AS avg_active_minutes,
            ROUND(AVG(sedentary_minutes), 2)
                AS avg_sedentary_minutes
        FROM daily_activity
        GROUP BY id
        ORDER BY avg_steps DESC
        """
    )

    # --------------------------------------------------------
    # USER FILTER
    # --------------------------------------------------------

    selected_user = st.selectbox(
        "Select a user",
        ["All Users"] + users["id"].astype(str).tolist()
    )

    if selected_user != "All Users":

        user_data = users[
            users["id"].astype(str) == selected_user
        ]

        row = user_data.iloc[0]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Activity Days",
            f"{int(row['activity_days'])}"
        )

        c2.metric(
            "Avg Steps",
            f"{row['avg_steps']:,.0f}"
        )

        c3.metric(
            "Avg Calories",
            f"{row['avg_calories']:,.0f}"
        )

        c4.metric(
            "Avg Active Minutes",
            f"{row['avg_active_minutes']:,.1f}"
        )

        st.markdown("---")

        individual = run_query(
            f"""
            SELECT
                activity_date,
                total_steps,
                calories,
                total_active_minutes,
                sedentary_minutes
            FROM daily_activity
            WHERE id = '{selected_user}'
            ORDER BY activity_date
            """
        )

        fig = px.line(
            individual,
            x="activity_date",
            y="total_steps",
            markers=True
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Steps"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.subheader("User Activity Summary")

        st.dataframe(
            users,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Average Steps by User")

        fig = px.bar(
            users.sort_values("avg_steps"),
            x="avg_steps",
            y="id",
            orientation="h"
        )

        fig.update_layout(
            xaxis_title="Average Steps",
            yaxis_title="User ID"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # USER SLEEP
    # --------------------------------------------------------

    st.subheader("😴 User Sleep Summary")

    user_sleep = run_query(
        """
        SELECT
            id,
            COUNT(*) AS sleep_records,
            ROUND(AVG(sleep_hours), 2)
                AS avg_sleep_hours,
            ROUND(AVG(time_in_bed_hours), 2)
                AS avg_time_in_bed
        FROM sleep_daily
        GROUP BY id
        ORDER BY avg_sleep_hours DESC
        """
    )

    st.dataframe(
        user_sleep,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SQL ANALYTICS
# ============================================================

elif page == "🧮 SQL Analytics":

    st.markdown(
        '<div class="main-title">🧮 SQL Analytics</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Explore predefined business questions answered using SQL."
    )

    query_catalog = [
        (
            "Average Daily Activity",
            """
            SELECT
                ROUND(AVG(total_steps), 2) AS avg_steps,
                ROUND(AVG(calories), 2) AS avg_calories,
                ROUND(AVG(total_active_minutes), 2)
                    AS avg_active_minutes
            FROM daily_activity
            """
        ),

        (
            "Top 10 Activity Days",
            """
            SELECT
                activity_date,
                ROUND(AVG(total_steps), 2) AS avg_steps,
                ROUND(AVG(calories), 2) AS avg_calories
            FROM daily_activity
            GROUP BY activity_date
            ORDER BY avg_steps DESC
            LIMIT 10
            """
        ),

        (
            "Activity by Day of Week",
            """
            SELECT
                day_name,
                ROUND(AVG(total_steps), 2) AS avg_steps,
                ROUND(AVG(calories), 2) AS avg_calories,
                ROUND(AVG(total_active_minutes), 2)
                    AS avg_active_minutes
            FROM daily_activity
            GROUP BY day_name
            ORDER BY avg_steps DESC
            """
        ),

        (
            "Top Activity Hours",
            """
            SELECT
                EXTRACT(HOUR FROM activity_hour) AS hour,
                ROUND(AVG(step_total), 2) AS avg_steps,
                ROUND(AVG(calories), 2) AS avg_calories
            FROM hourly_activity
            GROUP BY hour
            ORDER BY avg_steps DESC
            LIMIT 10
            """
        ),

        (
            "Sleep Categories",
            """
            SELECT
                CASE
                    WHEN sleep_hours < 5 THEN '<5 hours'
                    WHEN sleep_hours < 7 THEN '5–7 hours'
                    WHEN sleep_hours < 9 THEN '7–9 hours'
                    ELSE '9+ hours'
                END AS sleep_category,
                COUNT(*) AS records
            FROM sleep_daily
            GROUP BY sleep_category
            """
        ),

        (
            "User Activity Summary",
            """
            SELECT
                id,
                COUNT(*) AS activity_days,
                ROUND(AVG(total_steps), 2) AS avg_steps,
                ROUND(AVG(total_active_minutes), 2)
                    AS avg_active_minutes
            FROM daily_activity
            GROUP BY id
            ORDER BY avg_steps DESC
            """
        )
    ]

    question = st.selectbox(
        "Select a business question",
        [q[0] for q in query_catalog]
    )

    selected_query = dict(query_catalog)[question]

    st.code(
        selected_query.strip(),
        language="sql"
    )

    if st.button("▶ Run Analysis"):

        result = safe_query(selected_query)

        if result is not None:

            st.success(
                f"Query returned {len(result):,} rows."
            )

            st.dataframe(
                result,
                use_container_width=True,
                hide_index=True
            )

            csv = result.to_csv(index=False).encode("utf-8")

            st.download_button(
                "⬇️ Download Results",
                csv,
                "sql_analysis_results.csv",
                "text/csv"
            )

        else:

            st.error("The SQL query could not be executed.")


# ============================================================
# LIVE SQL PLAYGROUND
# ============================================================

elif page == "💻 Live SQL Playground":

    st.markdown(
        '<div class="main-title">💻 Live SQL Playground</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Write and execute read-only SQL queries directly against "
        "the project's DuckDB database."
    )

    st.info(
        "Only SELECT and WITH queries are allowed. "
        "Database modification commands are blocked."
    )

    # --------------------------------------------------------
    # TABLE SELECTOR
    # --------------------------------------------------------

    st.subheader("📚 Database Tables")

    selected_table = st.selectbox(
        "Select a table to inspect",
        TABLES
    )

    schema = run_query(
        f"""
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = '{selected_table}'
        ORDER BY ordinal_position
        """
    )

    st.dataframe(
        schema,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # SAMPLE DATA
    # --------------------------------------------------------

    if st.checkbox("Show sample rows"):

        sample = run_query(
            f"""
            SELECT *
            FROM {selected_table}
            LIMIT 10
            """
        )

        st.dataframe(
            sample,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # --------------------------------------------------------
    # EXAMPLE QUERIES
    # --------------------------------------------------------

    examples = {

        "Daily average steps":
            """
SELECT
    ROUND(AVG(total_steps), 2) AS avg_steps
FROM daily_activity;
""",

        "Top 10 users by average steps":
            """
SELECT
    id,
    ROUND(AVG(total_steps), 2) AS avg_steps
FROM daily_activity
GROUP BY id
ORDER BY avg_steps DESC
LIMIT 10;
""",

        "Activity by day of week":
            """
SELECT
    day_name,
    ROUND(AVG(total_steps), 2) AS avg_steps,
    ROUND(AVG(calories), 2) AS avg_calories
FROM daily_activity
GROUP BY day_name
ORDER BY avg_steps DESC;
""",

        "Top activity hours":
            """
SELECT
    EXTRACT(HOUR FROM activity_hour) AS hour,
    ROUND(AVG(step_total), 2) AS avg_steps
FROM hourly_activity
GROUP BY hour
ORDER BY avg_steps DESC
LIMIT 10;
""",

        "Average sleep":
            """
SELECT
    ROUND(AVG(sleep_hours), 2) AS avg_sleep_hours
FROM sleep_daily;
""",

        "Sleep and steps":
            """
SELECT
    ROUND(CORR(sleep_hours, total_steps), 3)
        AS sleep_steps_correlation
FROM activity_sleep;
"""
    }

    selected_example = st.selectbox(
        "Load an example query",
        ["Custom Query"] + list(examples.keys())
    )

    default_query = ""

    if selected_example != "Custom Query":
        default_query = examples[selected_example]

    # --------------------------------------------------------
    # SQL EDITOR
    # --------------------------------------------------------

    query = st.text_area(
        "SQL Query",
        value=default_query,
        height=250,
        placeholder="Write your SELECT query here..."
    )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    if st.button(
        "▶ Execute SQL",
        type="primary"
    ):

        valid, message = sql_is_safe(query)

        if not valid:

            st.error(message)

        else:

            try:

                start_time = time.perf_counter()

                result = con.execute(query).df()

                execution_time = (
                    time.perf_counter() - start_time
                )

                st.success(
                    f"Query executed successfully — "
                    f"{len(result):,} rows returned "
                    f"in {execution_time:.4f} seconds."
                )

                st.dataframe(
                    result,
                    use_container_width=True,
                    hide_index=True
                )

                # --------------------------------------------
                # DOWNLOAD
                # --------------------------------------------

                csv = result.to_csv(
                    index=False
                ).encode("utf-8")

                st.download_button(
                    "⬇️ Download Query Results",
                    csv,
                    "sql_query_results.csv",
                    "text/csv"
                )

                # --------------------------------------------
                # RESULT INFORMATION
                # --------------------------------------------

                st.caption(
                    f"Rows returned: {len(result):,} | "
                    f"Columns: {len(result.columns)} | "
                    f"Execution time: {execution_time:.4f}s"
                )

            except Exception as e:

                st.error(
                    f"SQL Error: {str(e)}"
                )


# ============================================================
# DATA QUALITY & METHODOLOGY
# ============================================================

elif page == "📋 Data Quality & Methodology":

    st.markdown(
        '<div class="main-title">📋 Data Quality & Methodology</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Documentation of the datasets, validation process and "
        "analytical model used in this project."
    )

    # --------------------------------------------------------
    # TABLE SUMMARY
    # --------------------------------------------------------

    st.subheader("📊 Analytical Tables")

    table_summary = run_query(
        """
        SELECT
            'daily_activity' AS table_name,
            COUNT(*) AS rows,
            COUNT(DISTINCT id) AS users
        FROM daily_activity

        UNION ALL

        SELECT
            'hourly_activity',
            COUNT(*),
            COUNT(DISTINCT id)
        FROM hourly_activity

        UNION ALL

        SELECT
            'sleep_daily',
            COUNT(*),
            COUNT(DISTINCT id)
        FROM sleep_daily

        UNION ALL

        SELECT
            'activity_sleep',
            COUNT(*),
            COUNT(DISTINCT id)
        FROM activity_sleep
        """
    )

    st.dataframe(
        table_summary,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # DATE COVERAGE
    # --------------------------------------------------------

    st.subheader("📅 Data Coverage")

    coverage = run_query(
        """
        SELECT
            MIN(activity_date) AS start_date,
            MAX(activity_date) AS end_date,
            COUNT(DISTINCT activity_date) AS dates,
            COUNT(DISTINCT id) AS users
        FROM daily_activity
        """
    )

    st.dataframe(
        coverage,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    st.subheader("✅ Data Validation")

    duplicate_check = run_query(
        """
        SELECT
            'daily_activity' AS table_name,
            COUNT(*) -
            COUNT(DISTINCT
                CAST(id AS VARCHAR)
                || CAST(activity_date AS VARCHAR)
            ) AS duplicate_keys
        FROM daily_activity

        UNION ALL

        SELECT
            'hourly_activity',
            COUNT(*) -
            COUNT(DISTINCT
                CAST(id AS VARCHAR)
                || CAST(activity_hour AS VARCHAR)
            )
        FROM hourly_activity

        UNION ALL

        SELECT
            'sleep_daily',
            COUNT(*) -
            COUNT(DISTINCT
                CAST(id AS VARCHAR)
                || CAST(activity_date AS VARCHAR)
            )
        FROM sleep_daily

        UNION ALL

        SELECT
            'activity_sleep',
            COUNT(*) -
            COUNT(DISTINCT
                CAST(id AS VARCHAR)
                || CAST(activity_date AS VARCHAR)
            )
        FROM activity_sleep
        """
    )

    st.dataframe(
        duplicate_check,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # METHODOLOGY
    # --------------------------------------------------------

    st.subheader("🔎 Methodology")

    st.markdown(
        """
        **Data preparation**

        - Raw fitness-tracking datasets were inspected and cleaned.
        - Duplicate records were identified and handled.
        - Date and time fields were standardized.
        - Daily, hourly and sleep datasets were validated.
        - Multiple duplicate heart-rate source files were identified.
        - Minute-level datasets were retained separately rather than
          unnecessarily merging them into the core analytical model.

        **Core analytical model**

        - `daily_activity` — user-date level activity data.
        - `hourly_activity` — user-hour level activity data.
        - `sleep_daily` — user-date level sleep data.
        - `activity_sleep` — matched user-date activity and sleep data.

        **SQL layer**

        DuckDB is used as the analytical database.

        **Dashboard**

        Streamlit provides the interactive user interface and
        Plotly provides interactive visualizations.

        **Live SQL Playground**

        Users can execute read-only `SELECT` and `WITH` queries
        directly against the DuckDB database.
        """
    )

    # --------------------------------------------------------
    # DATABASE SCHEMA
    # --------------------------------------------------------

    st.subheader("🗂️ Database Schema")

    schema = run_query(
        """
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name IN (
            'daily_activity',
            'hourly_activity',
            'sleep_daily',
            'activity_sleep'
        )
        ORDER BY
            table_name,
            ordinal_position
        """
    )

    st.dataframe(
        schema,
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# FOOTER
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "Fitness Analytics • Python • SQL • DuckDB • Streamlit • Plotly"
)