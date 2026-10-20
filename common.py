import gzip, json
from pathlib import Path
import duckdb, pandas as pd, streamlit as st

DATA = Path(__file__).parent / "data"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRAY = "#b5b4ae"
DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]          # DuckDB dayofweek: 0 = Sunday


@st.cache_resource
def _db():
    return duckdb.connect(str(DATA / "dashboard.duckdb"), read_only=True)


@st.cache_data
def q(sql, params=None):
    with _db().cursor() as cur:                                   # one cursor per query: safe across sessions
        return cur.execute(sql, params or []).df()


@st.cache_data
def zones():
    z = q("SELECT * FROM zones ORDER BY zone")
    z["name"] = z.zone + " (" + z.borough + ")"
    return z


@st.cache_data
def geojson():
    return json.loads((DATA / "taxi_zones.geojson").read_text())


@st.cache_data
def metrics():
    return json.loads((DATA / "metrics.json").read_text())


@st.cache_resource
def booster(name):
    import lightgbm as lgb
    with gzip.open(DATA / "models" / f"{name}.txt.gz", "rt") as f:
        return lgb.Booster(model_str=f.read())


def style(fig, height=320):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=40, b=40),
                      colorway=C, font=dict(size=13), title_font=dict(size=16),
                      legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, title=None))
    fig.update_xaxes(showgrid=False, title=None)
    return fig
