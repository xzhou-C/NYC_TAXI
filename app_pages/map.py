import numpy as np, pandas as pd, plotly.express as px, streamlit as st
from common import q, zones, geojson, style, C, DOW

st.title("Where the pickups are")
z = zones()
c1, c2 = st.columns([1, 2])
days = c1.segmented_control("Days", ["All days", "Weekdays", "Weekends"], default="All days")
h0, h1 = c2.slider("Pickup hour", 0, 23, (0, 23), format="%d:00")
dows = {"All days": range(7), "Weekdays": range(1, 6), "Weekends": (0, 6)}[days or "All days"]

prof = q("SELECT * FROM zone_profile")
win = prof[prof.dow.isin(list(dows)) & prof.hour.between(h0, h1)]
by_zone = (win.groupby("locationid").avg_pickups.mean().rename("per_hour").reset_index()
             .merge(z[["locationid", "zone", "borough"]], on="locationid"))
by_zone["log"] = np.log10(by_zone.per_hour.clip(lower=0.1))       # log color scale, labeled in real numbers

ticks = [0.1, 1, 10, 100, 1000]
# Drawn as SVG with no basemap tiles, so it loads fast and works anywhere
fig = px.choropleth(by_zone, geojson=geojson(), locations="locationid", featureidkey="properties.locationid",
                    color="log", color_continuous_scale="Blues", range_color=(-1, np.log10(max(by_zone.per_hour.max(), 1))),
                    hover_name="zone", hover_data={"borough": True, "per_hour": ":.1f", "log": False, "locationid": False},
                    labels={"per_hour": "Pickups per hour"})
fig.update_geos(fitbounds="locations", visible=False)
fig.update_traces(marker_line_color="white", marker_line_width=0.4)
fig.update_coloraxes(colorbar=dict(title="Pickups<br>per hour", tickvals=np.log10(ticks), ticktext=["0.1", "1", "10", "100", "1,000"]))
fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig)
st.caption(f"Average pickups per hour, {days.lower() if days else 'all days'}, {h0}:00–{h1}:59. "
           "Hover a zone for its number; pick one below for its trend.")

default = int(by_zone.sort_values("per_hour").locationid.iloc[-1])      # the busiest zone in the current filter
names = z.set_index("locationid")["name"]
zone_id = st.selectbox("Zone", z.locationid, index=int(np.flatnonzero(z.locationid == default)[0]),
                       format_func=lambda i: names[i])

a, b = st.columns(2)
wk = q("SELECT week, pickups FROM zone_weekly WHERE locationid = ? ORDER BY week", [int(zone_id)])
f1 = px.line(wk, x="week", y="pickups", title=f"Weekly pickups: {names[zone_id]}", color_discrete_sequence=[C[0]])
f1.update_yaxes(title=None, rangemode="tozero")
a.plotly_chart(style(f1))

zp = prof[prof.locationid == zone_id].assign(day=lambda x: np.where(x.dow.isin([0, 6]), "Weekend", "Weekday"))
zp = zp.groupby(["day", "hour"]).avg_pickups.mean().reset_index()
f2 = px.line(zp, x="hour", y="avg_pickups", color="day", title="Average pickups by hour",
             color_discrete_map={"Weekday": C[0], "Weekend": C[1]})
f2.update_xaxes(tickvals=list(range(0, 24, 3)), ticktext=[f"{h}:00" for h in range(0, 24, 3)])
f2.update_yaxes(title=None, rangemode="tozero")
b.plotly_chart(style(f2))
