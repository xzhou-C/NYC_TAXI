import pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from common import q, style, C, GRAY

st.title("NYC yellow cab trips")
d = q("SELECT * FROM daily_summary ORDER BY date")
d["date"] = pd.to_datetime(d.date)
st.caption(f"{d.trips.sum() / 1e6:,.1f} million clean trips, {d.date.min():%b %Y} to {d.date.max():%b %Y}. "
           "Source: NYC TLC trip records.")

# Monthly figures. Average fare is weighted by trips, so it equals total fares / total trips for the month.
m = (d.assign(month=d.date.dt.to_period("M"), fare_x_trips=d.avg_fare * d.trips)
       .groupby("month").agg(days=("date", "size"), trips=("trips", "sum"), revenue=("revenue", "sum"),
                             fare_x_trips=("fare_x_trips", "sum"), tip=("median_tip_pct_card", "mean")))
m["trips_per_day"], m["revenue_per_day"] = m.trips / m.days, m.revenue / m.days
m["avg_fare"] = m.fare_x_trips / m.trips

months = [str(p) for p in m.index]
pick = st.select_slider("Month", options=months, value=months[-1],
                        format_func=lambda s: pd.Period(s).strftime("%b %Y"))
cur = m.loc[pd.Period(pick)]
prev = m.shift(1).loc[pd.Period(pick)]


def delta(a, b, fmt):
    return None if pd.isna(a) or pd.isna(b) else fmt(a - b)


k = st.columns(4)
k[0].metric("Trips per day", f"{cur.trips_per_day:,.0f}",
            delta(cur.trips_per_day / prev.trips_per_day * 100, 100, lambda x: f"{x:+.1f}% vs. prior month"))
k[1].metric("Revenue per day", f"${cur.revenue_per_day / 1e6:,.2f}M",
            delta(cur.revenue_per_day / prev.revenue_per_day * 100, 100, lambda x: f"{x:+.1f}%"))
k[2].metric("Average fare", f"${cur.avg_fare:,.2f}", delta(cur.avg_fare, prev.avg_fare, lambda x: f"{x:+.2f}"))
k[3].metric("Median tip (card trips)", f"{cur.tip:.1f}%", delta(cur.tip, prev.tip, lambda x: f"{x:+.1f} pts"))

d["avg7"] = d.trips.rolling(7, center=True).mean()
fig = go.Figure()
fig.add_scatter(x=d.date, y=d.trips, mode="lines", line=dict(color=GRAY, width=1), name="Daily")
fig.add_scatter(x=d.date, y=d.avg7, mode="lines", line=dict(color=C[0], width=2.5), name="7-day average")
sel = pd.Period(pick)
fig.add_vrect(x0=sel.start_time, x1=sel.end_time, fillcolor=C[0], opacity=0.08, line_width=0)
fig.update_yaxes(title="Trips per day")
st.plotly_chart(style(fig.update_layout(title="Trips per day"), 340))

left, right = st.columns(2)
mm = m.reset_index().assign(month=lambda x: x.month.dt.to_timestamp())
f2 = px.bar(mm, x="month", y="revenue_per_day", title="Revenue per day, by month", color_discrete_sequence=[C[0]])
f2.update_yaxes(title=None, tickprefix="$", rangemode="tozero")
left.plotly_chart(style(f2, 300))
f3 = px.line(mm, x="month", y="avg_fare", markers=True, title="Average fare, by month", color_discrete_sequence=[C[1]])
f3.update_yaxes(title=None, tickprefix="$")
right.plotly_chart(style(f3, 300))
