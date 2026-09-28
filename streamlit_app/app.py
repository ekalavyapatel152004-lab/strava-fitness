import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from streamlit.delta_generator import DeltaGenerator
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
# GLOW DASHBOARD THEME  (CSS + Plotly template + KPI cards)
# ============================================================

GLOW_COLORWAY = [
    "#3b82f6", "#f59e0b", "#22d3ee", "#a78bfa",
    "#34d399", "#f472b6", "#f87171"
]

BAR_SCALE = [[0, "#1d4ed8"], [0.55, "#3b82f6"], [1, "#22d3ee"]]
HEAT_SCALE = [
    [0, "#071433"], [0.25, "#1e40af"], [0.5, "#3b82f6"],
    [0.75, "#22d3ee"], [1, "#e0f2fe"]
]

st.markdown(
    """
    <style>
        html, body, .stApp, [class*="css"] {
            font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif;
        }

        /* ---------- BACKGROUND ---------- */
        .stApp {
            background:
                radial-gradient(1100px 560px at 12% -8%, rgba(37,99,235,.30), transparent 60%),
                linear-gradient(180deg, #040a1c 0%, #071433 55%, #050b1f 100%);
            color: #e2e8f0;
        }

        header[data-testid="stHeader"] { background: transparent; }

        .block-container {
            padding-top: 2rem;
            max-width: 1500px;
        }

        /* ---------- SIDEBAR ---------- */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #060e26 0%, #08163a 100%);
            border-right: 1px solid rgba(59,130,246,.28);
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 6px;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] > label {
            width: 100%;
            padding: 10px 14px;
            border-radius: 12px;
            border: 1px solid transparent;
            background: rgba(15,35,85,.35);
            transition: border-color .15s ease;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
            display: none;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: rgba(96,165,250,.5);
            box-shadow: 0 0 16px rgba(59,130,246,.28);
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(90deg, rgba(37,99,235,.6), rgba(34,211,238,.18));
            border-color: #3b82f6;
            box-shadow: 0 0 22px rgba(59,130,246,.5);
        }

        /* ---------- TITLES ---------- */
        .main-title {
            font-size: 2.3rem;
            font-weight: 800;
            margin-bottom: .2rem;
            letter-spacing: -.5px;
            background: linear-gradient(90deg, #ffffff 0%, #93c5fd 45%, #22d3ee 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: .98rem;
            color: #94a3b8;
            margin-bottom: 1.2rem;
        }

        .subtitle .live {
            color: #34d399;
            font-weight: 600;
            text-shadow: 0 0 10px rgba(52,211,153,.8);
            margin-left: 6px;
        }

        .section-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin: 1rem 0 .5rem 0;
        }

        div[data-testid="stMarkdownContainer"] h3 {
            font-size: 1.05rem !important;
            font-weight: 650 !important;
            color: #e2e8f0;
            padding-left: 12px;
            border-left: 3px solid #3b82f6;
            box-shadow: -6px 0 14px -6px rgba(59,130,246,.9);
            margin: .6rem 0 .6rem 0;
        }

        hr {
            border: none !important;
            height: 1px !important;
            margin: 1.4rem 0 !important;
            background: linear-gradient(90deg, transparent, rgba(96,165,250,.7), transparent) !important;
            box-shadow: 0 0 12px rgba(59,130,246,.7);
        }

        .small-note { font-size: .85rem; color: #94a3b8; }

        /* ---------- KPI CARDS ---------- */
        .kpi {
            --acc: #3b82f6;
            position: relative;
            padding: 15px 18px 13px 18px;
            margin-bottom: 12px;
            border-radius: 16px;
            background: linear-gradient(145deg, rgba(22,50,115,.68), rgba(8,20,55,.78));
            border: 1px solid rgba(96,165,250,.28);
            box-shadow:
                0 8px 28px rgba(2,8,30,.6),
                0 0 26px color-mix(in srgb, var(--acc) 20%, transparent),
                inset 0 1px 0 rgba(255,255,255,.06);
            transition: transform .2s ease, border-color .2s ease;
            overflow: hidden;
        }

        .kpi:hover {
            transform: translateY(-3px);
            border-color: var(--acc);
        }

        .kpi-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .kpi-label {
            font-size: .78rem;
            font-weight: 600;
            color: #cbd5e1;
            letter-spacing: .2px;
        }

        .kpi-ico {
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border-radius: 9px;
            font-size: .95rem;
            background: color-mix(in srgb, var(--acc) 24%, transparent);
            box-shadow: 0 0 14px color-mix(in srgb, var(--acc) 55%, transparent);
        }

        .kpi-val {
            margin-top: 8px;
            font-size: 1.75rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.1;
            text-shadow: 0 0 18px color-mix(in srgb, var(--acc) 65%, transparent);
        }

        .kpi-delta {
            margin-top: 4px;
            font-size: .74rem;
            font-weight: 600;
        }

        .kpi-delta.up { color: #34d399; }
        .kpi-delta.down { color: #f87171; }
        .kpi-delta.flat { color: #94a3b8; }

        .kpi-line {
            height: 2px;
            margin-top: 11px;
            border-radius: 2px;
            background: linear-gradient(90deg, var(--acc), transparent);
            box-shadow: 0 0 10px var(--acc);
        }

        /* ---------- CHART / TABLE CARDS ---------- */
        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            padding: 10px;
            border-radius: 16px;
            background: linear-gradient(160deg, rgba(14,34,84,.55), rgba(6,16,44,.7));
            border: 1px solid rgba(96,165,250,.24);
            box-shadow: 0 4px 14px rgba(2,8,30,.45);
        }

        .glass {
            padding: 14px 16px;
            border-radius: 16px;
            background: linear-gradient(160deg, rgba(14,34,84,.55), rgba(6,16,44,.7));
            border: 1px solid rgba(96,165,250,.24);
            box-shadow: 0 10px 30px rgba(2,8,30,.55), 0 0 24px rgba(37,99,235,.16);
        }

        table.glow-table {
            width: 100%;
            border-collapse: collapse;
            font-size: .85rem;
        }

        table.glow-table th {
            text-align: left;
            font-weight: 600;
            font-size: .72rem;
            text-transform: uppercase;
            letter-spacing: .6px;
            color: #94a3b8;
            padding: 8px 10px;
            border-bottom: 1px solid rgba(96,165,250,.25);
        }

        table.glow-table td {
            padding: 11px 10px;
            color: #e2e8f0;
            border-bottom: 1px solid rgba(96,165,250,.10);
        }

        table.glow-table tr:hover td { background: rgba(59,130,246,.10); }
        table.glow-table td.num { font-variant-numeric: tabular-nums; }

        table.glow-table td.rk span {
            display: inline-grid;
            place-items: center;
            width: 24px;
            height: 24px;
            border-radius: 8px;
            font-weight: 700;
            font-size: .75rem;
            background: rgba(59,130,246,.25);
            box-shadow: 0 0 12px rgba(59,130,246,.55);
        }

        table.glow-table .bar {
            width: 100%;
            min-width: 90px;
            height: 7px;
            border-radius: 7px;
            background: rgba(148,163,184,.15);
        }

        table.glow-table .bar span {
            display: block;
            height: 100%;
            border-radius: 7px;
            background: linear-gradient(90deg, #3b82f6, #22d3ee);
            box-shadow: 0 0 10px rgba(34,211,238,.8);
        }

        /* ---------- INPUTS & BUTTONS ---------- */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"],
        div[data-baseweb="textarea"],
        textarea {
            background: rgba(13,30,70,.65) !important;
            border-color: rgba(96,165,250,.3) !important;
            border-radius: 10px !important;
        }

        button[kind="primary"] {
            background: linear-gradient(90deg, #2563eb, #0ea5e9) !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            box-shadow: 0 0 22px rgba(37,99,235,.6);
            transition: box-shadow .15s ease;
        }

        button[kind="primary"]:hover {
            box-shadow: 0 0 32px rgba(34,211,238,.75);
            transform: translateY(-1px);
        }

        div[data-testid="stAlert"] {
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# PLOTLY TEMPLATE  (dark + transparent + soft grid)
# ------------------------------------------------------------

_axis_style = dict(
    gridcolor="rgba(148,163,184,0.10)",
    zeroline=False,
    linecolor="rgba(148,163,184,0.25)",
    tickfont=dict(color="#94a3b8"),
    title=dict(font=dict(color="#94a3b8"))
)

pio.templates["glow"] = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family="Inter, Segoe UI, Roboto, sans-serif",
            color="#cbd5e1",
            size=12
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=GLOW_COLORWAY,
        xaxis=_axis_style,
        yaxis=_axis_style,
        hoverlabel=dict(
            bgcolor="#0b1533",
            bordercolor="#3b82f6",
            font=dict(color="#e2e8f0")
        ),
        legend=dict(font=dict(color="#cbd5e1")),
        margin=dict(l=40, r=20, t=40, b=40),
        colorscale=dict(sequential=HEAT_SCALE)
    )
)

pio.templates.default = "plotly_dark+glow"


def _rgba(color, alpha):
    """Convert hex / rgb / rgba color to rgba with a given alpha."""
    if color is None:
        return f"rgba(59,130,246,{alpha})"
    color = str(color)
    if color.startswith("#"):
        h = color.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    if color.startswith("rgba("):
        parts = color[5:-1].split(",")[:3]
        return f"rgba({','.join(parts)},{alpha})"
    if color.startswith("rgb("):
        return color.replace("rgb(", "rgba(").replace(")", f",{alpha})")
    return color


def apply_glow(fig):
    """
    Light, readable styling applied to every Plotly figure:
    solid lines, clear markers, gradient bars. No area fills and no
    wide glow layers (those hid the lines and made charts muddy).
    """
    bars = [t for t in fig.data if t.type == "bar"]

    for t in fig.data:

        if t.type == "scatter":
            mode = t.mode or ""

            if "lines" in mode:
                t.update(line=dict(width=max(t.line.width or 0, 2.5)))

            if "markers" in mode and "lines" in mode:
                t.update(marker=dict(
                    size=6,
                    line=dict(color="#050b1f", width=1)
                ))
            elif mode == "markers":
                t.update(marker=dict(size=8, opacity=0.65, line=dict(width=0)))

        elif t.type == "bar":
            done = False
            if len(bars) == 1:
                try:
                    values = t.x if t.orientation == "h" else t.y
                    vals = [float(v) for v in values]
                    t.update(marker=dict(
                        color=vals,
                        colorscale=BAR_SCALE,
                        showscale=False,
                        line=dict(width=0)
                    ))
                    done = True
                except Exception:
                    done = False
            if not done:
                t.update(marker=dict(line=dict(width=0)))

        elif t.type == "heatmap":
            t.update(colorscale=HEAT_SCALE, xgap=2, ygap=2)

    fig.update_layout(
        bargap=0.25,
        legend=dict(
            orientation="h", y=1.1, x=0,
            title_text="", bgcolor="rgba(0,0,0,0)"
        )
    )
    if fig.layout.height is None:
        fig.update_layout(height=400)

    return fig


# Every st.plotly_chart(...) in the app now gets the glow look
# automatically - no need to edit each chart.
_original_plotly_chart = st.plotly_chart


def _glow_plotly_chart(fig, *args, **kwargs):
    kwargs.setdefault("theme", None)
    try:
        fig = apply_glow(fig)
    except Exception:
        pass
    return _original_plotly_chart(fig, *args, **kwargs)


st.plotly_chart = _glow_plotly_chart

# ------------------------------------------------------------
# KPI CARDS  (replaces the plain st.metric look)
# ------------------------------------------------------------

_KPI_STYLE = [
    ("user", "👥", "#3b82f6"),
    ("record", "🗂️", "#a78bfa"),
    ("sedentary", "🪑", "#f87171"),
    ("active", "⚡", "#34d399"),
    ("step", "👟", "#22d3ee"),
    ("calor", "🔥", "#f59e0b"),
    ("bed", "🛏️", "#818cf8"),
    ("sleep", "😴", "#818cf8"),
    ("hour", "⏰", "#22d3ee"),
    ("median", "📊", "#a78bfa"),
]


def _kpi_card(self, label, value, delta=None, delta_color="normal", *args, **kwargs):
    text = str(label).lower()
    icon, accent = "📌", "#3b82f6"

    for key, ico, col in _KPI_STYLE:
        if key in text:
            icon, accent = ico, col
            break

    delta_html = ""
    if delta is not None:
        d = str(delta)
        negative = d.strip().startswith("-")
        cls = "down" if negative else "up"
        if delta_color == "inverse":
            cls = "up" if negative else "down"
        elif delta_color == "off":
            cls = "flat"
        arrow = "▼" if negative else "▲"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {d.lstrip("+-")}</div>'

    html = (
        f'<div class="kpi" style="--acc:{accent}">'
        f'<div class="kpi-top"><span class="kpi-label">{label}</span>'
        f'<span class="kpi-ico">{icon}</span></div>'
        f'<div class="kpi-val">{value}</div>'
        f'{delta_html}<div class="kpi-line"></div></div>'
    )

    return self.markdown(html, unsafe_allow_html=True)


DeltaGenerator.metric = _kpi_card
st.metric = lambda *a, **k: _kpi_card(st._main, *a, **k)


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

@st.cache_data(show_spinner=False)
def run_query(query):
    # cursor() gives each Streamlit thread its own connection handle
    return con.cursor().execute(query).df()


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
        '<div class="subtitle">Track activity, calories, sleep and recovery '
        'across every user <span class="live">● Live from DuckDB</span></div>',
        unsafe_allow_html=True
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

    c1.metric("Users", f"{int(kpi['users'])}")
    c2.metric("Activity Records", f"{int(kpi['records']):,}")
    c3.metric("Avg Steps", format_number(kpi["avg_steps"]))
    c4.metric("Avg Calories", format_number(kpi["avg_calories"]))
    c5.metric("Avg Active Minutes", f"{kpi['avg_active_minutes']:.1f}")
    c6.metric("Avg Sleep", f"{sleep_kpi['avg_sleep']:.2f} hrs")

    # --------------------------------------------------------
    # ROW 1: TREND (area + glow)  |  STEPS BY WEEKDAY
    # --------------------------------------------------------

    left, right = st.columns([3, 2])

    with left:

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

        trend["steps_7d"] = (
            trend["avg_steps"].rolling(7, min_periods=1).mean()
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=trend["activity_date"],
                y=trend["avg_steps"],
                mode="lines+markers",
                name="Average Steps",
                line=dict(color="#3b82f6", width=3)
            )
        )

        fig.add_trace(
            go.Scatter(
                x=trend["activity_date"],
                y=trend["steps_7d"],
                mode="lines",
                name="7-day average",
                line=dict(color="#22d3ee", width=2, dash="dot")
            )
        )

        fig.update_layout(
            height=380,
            hovermode="x unified",
            xaxis_title=None,
            yaxis_title="Average Steps"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:

        st.subheader("📅 Steps by Weekday")

        weekday = run_query(
            """
            SELECT
                day_name,
                ROUND(AVG(total_steps), 2) AS avg_steps
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

        weekday["day"] = weekday["day_name"].str[:3]

        fig = px.bar(
            weekday,
            x="day",
            y="avg_steps",
            text="avg_steps"
        )

        fig.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=10),
            cliponaxis=False
        )

        fig.update_layout(
            height=380,
            xaxis_title=None,
            yaxis_title=None
        )

        st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------------
    # ROW 2: DONUT  |  TOP DAYS TABLE
    # --------------------------------------------------------

    left, right = st.columns([2, 3])

    with left:

        st.subheader("⚖️ Active vs Sedentary Time")

        active = float(kpi["avg_active_minutes"])
        sedentary = float(kpi["avg_sedentary_minutes"])
        share = active / (active + sedentary) * 100

        fig = go.Figure(
            go.Pie(
                labels=[
                    f"Active · {active:,.0f} min",
                    f"Sedentary · {sedentary:,.0f} min"
                ],
                values=[active, sedentary],
                hole=0.74,
                sort=False,
                marker=dict(
                    colors=["#22d3ee", "#3b82f6"],
                    line=dict(color="#071433", width=3)
                ),
                textinfo="none",
                hovertemplate="%{label}<br>%{percent}<extra></extra>"
            )
        )

        fig.update_layout(
            height=330,
            showlegend=True,
            legend=dict(
                orientation="h",
                y=-0.05,
                x=0.5,
                xanchor="center"
            ),
            annotations=[
                dict(
                    text=(
                        f"<b>{share:.0f}%</b><br>"
                        "<span style='font-size:12px;color:#94a3b8'>"
                        "active time</span>"
                    ),
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=30, color="#ffffff")
                )
            ]
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:

        st.subheader("🏆 Top 5 Activity Days")

        top5 = run_query(
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
            LIMIT 5
            """
        )

        max_steps = top5["avg_steps"].max()

        rows_html = ""

        for rank, row in enumerate(top5.itertuples(), start=1):

            day = pd.to_datetime(row.activity_date).strftime("%d %b %Y")
            pct = row.avg_steps / max_steps * 100

            rows_html += (
                f'<tr><td class="rk"><span>{rank}</span></td>'
                f'<td>{day}</td>'
                f'<td class="num">{row.avg_steps:,.0f}</td>'
                f'<td class="num">{row.avg_calories:,.0f}</td>'
                f'<td class="num">{row.avg_active_minutes:,.1f}</td>'
                f'<td><div class="bar"><span style="width:{pct:.0f}%">'
                f'</span></div></td></tr>'
            )

        st.markdown(
            '<div class="glass"><table class="glow-table">'
            '<thead><tr><th>#</th><th>Date</th><th>Avg Steps</th>'
            '<th>Calories</th><th>Active Min</th><th>vs Best</th></tr>'
            f'</thead><tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # ROW 3: WEEKDAY VS WEEKEND  |  SLEEP SUMMARY CARDS
    # --------------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.subheader("🗓️ Weekday vs Weekend")

        day_type = run_query(
            """
            SELECT
                day_type,
                ROUND(AVG(total_steps), 2) AS avg_steps
            FROM daily_activity
            GROUP BY day_type
            """
        )

        fig = px.bar(
            day_type,
            x="day_type",
            y="avg_steps",
            text="avg_steps"
        )

        fig.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=12),
            cliponaxis=False
        )

        fig.update_layout(
            height=340,
            xaxis_title=None,
            yaxis_title="Average Steps"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:

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
        ).iloc[0]

        efficiency = (
            sleep_summary["avg_sleep_hours"]
            / sleep_summary["avg_time_in_bed"] * 100
        )

        s1, s2 = st.columns(2)
        s1.metric("Sleep Records", f"{int(sleep_summary['records']):,}")
        s2.metric("Sleep Users", f"{int(sleep_summary['users'])}")

        s3, s4 = st.columns(2)
        s3.metric("Avg Sleep Hours", f"{sleep_summary['avg_sleep_hours']:.2f}")
        s4.metric("Median Sleep", f"{sleep_summary['median_sleep_hours']:.2f}")

        s5, s6 = st.columns(2)
        s5.metric("Avg Time In Bed", f"{sleep_summary['avg_time_in_bed']:.2f}")
        s6.metric("Sleep Efficiency", f"{efficiency:.1f}%")


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

        fig.for_each_trace(lambda t: t.update(
            name={
                "total_active_minutes": "Active minutes",
                "sedentary_minutes": "Sedentary minutes"
            }.get(t.name, t.name)
        ))

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
        markers=True,
        color_discrete_map={"Weekday": "#3b82f6", "Weekend": "#f59e0b"}
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
        opacity=0.6,
        labels={
            "sleep_hours": "Sleep Hours",
            "total_steps": "Total Steps"
        }
    )

    _clean = scatter[["sleep_hours", "total_steps"]].dropna()
    if len(_clean) > 1:
        slope, intercept = np.polyfit(
            _clean["sleep_hours"], _clean["total_steps"], 1
        )
        _xs = np.array([_clean["sleep_hours"].min(), _clean["sleep_hours"].max()])
        fig.add_trace(
            go.Scatter(
                x=_xs,
                y=slope * _xs + intercept,
                mode="lines",
                name="Trend (OLS)",
                line=dict(color="#f59e0b", width=3)
            )
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

        users_plot = users.sort_values("avg_steps").copy()
        users_plot["id"] = users_plot["id"].astype(str)

        fig = px.bar(
            users_plot,
            x="avg_steps",
            y="id",
            orientation="h"
        )

        fig.update_layout(
            xaxis_title="Average Steps",
            yaxis_title="User ID",
            yaxis=dict(type="category", tickfont=dict(size=10)),
            height=max(420, 24 * len(users_plot))
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