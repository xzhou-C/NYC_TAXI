import pandas as pd, plotly.graph_objects as go, plotly.express as px, streamlit as st
from common import q, metrics, style, C, GRAY

st.title("Demand forecast: next 7 days")
fc = q("SELECT * FROM forecast ORDER BY unique_id, ds")
act = q("SELECT * FROM forecast_actuals ORDER BY unique_id, ds")
bt = metrics()["forecast"]
best = bt["best_model"]
st.caption(f"Hourly pickups forecast by {best}, made {pd.Timestamp(fc.made_at.iloc[0]):%b %-d, %Y}, "
           f"for {fc.ds.min():%a %b %-d} to {fc.ds.max():%a %b %-d}.")

labels = fc.groupby("unique_id").label.first().sort_values()
default = labels.index.get_loc("z161") if "z161" in labels.index else 0
uid = st.selectbox("Zone", labels.index, index=default, format_func=lambda u: labels[u])

f, a = fc[fc.unique_id == uid], act[act.unique_id == uid]
fig = go.Figure()
fig.add_scatter(x=a.ds, y=a.y, mode="lines", line=dict(color=GRAY, width=1.5), name="Last 14 days (actual)")
fig.add_scatter(x=f.ds, y=f.forecast, mode="lines", line=dict(color=C[0], width=2), name="Forecast")
fig.add_vline(x=f.ds.min().isoformat(), line_dash="dot", line_color="#52514e")
fig.update_yaxes(title="Pickups per hour", rangemode="tozero")
st.plotly_chart(style(fig.update_layout(title=labels[uid]), 360))

peak = f.loc[f.forecast.idxmax()]
last_week = a[a.ds >= f.ds.min() - pd.Timedelta(days=7)].y.sum()
k = st.columns(3)
k[0].metric("Pickups next 7 days", f"{f.forecast.sum():,.0f}",
            f"{(f.forecast.sum() / last_week - 1) * 100:+.0f}% vs. last 7 days" if last_week else None)
k[1].metric(f"Busiest hour ({peak.forecast:,.0f} pickups)", f"{peak.ds:%a %-I %p}")
k[2].metric(f"Backtest error, WAPE (same-hour-last-week: {bt['overall']['Seasonal naive']['WAPE']:.0%})",
            f"{bt['overall'][best]['WAPE']:.0%}")

st.subheader("How accurate is it?")
st.caption("Rolling-origin backtest: 12 times, the model forecast a week it hadn't seen. "
           "MASE below 1 beats the same-hour-last-week forecast. WAPE is the share of pickups mispredicted.")
left, right = st.columns([3, 2])
ov = pd.DataFrame(bt["overall"]).T[["MASE", "WAPE"]]
left.dataframe(ov.style.format({"MASE": "{:.2f}", "WAPE": "{:.1%}"}))
bb = pd.DataFrame(bt["by_borough_WAPE"]).T
bb = bb.loc[[b for b in ["Manhattan", "Queens", "Brooklyn", "Bronx"] if b in bb.index], [best]].reset_index()
f2 = px.bar(bb, x=best, y="index", orientation="h", title=f"{best}: WAPE by borough", color_discrete_sequence=[C[0]])
f2.update_xaxes(tickformat=".0%", title=None)
f2.update_yaxes(title=None, autorange="reversed")
right.plotly_chart(style(f2, 260))
