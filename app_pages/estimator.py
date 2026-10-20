import datetime as dt
import holidays, numpy as np, pandas as pd, plotly.express as px, streamlit as st
from common import zones, booster, metrics, style, C

st.title("Trip estimator")
st.caption("Predicted from what's known at booking: pickup and drop-off zone and time. Standard metered trips.")
z = zones().set_index("locationid")
ids = list(z.index)
default_pu = 161 if 161 in ids else ids[0]
default_do = 132 if 132 in ids else ids[-1]

c = st.columns([2, 2, 1, 1])
pu = c[0].selectbox("Pickup zone", ids, index=ids.index(default_pu), format_func=lambda i: z["name"][i])
do = c[1].selectbox("Drop-off zone", ids, index=ids.index(default_do), format_func=lambda i: z["name"][i])
day = c[2].date_input("Date", dt.date.today() + dt.timedelta(days=1))
t = c[3].time_input("Pickup time", dt.time(17, 0), step=1800)
NY_HOLIDAYS = holidays.US(state="NY", years=range(2024, dt.date.today().year + 3))


def features(hours):
    """One row per pickup hour, built the same way as the Phase 3 modeling table."""
    a, b = z.loc[pu], z.loc[do]
    dow = (day.weekday() + 1) % 7                                  # 0 = Sunday, as in DuckDB
    f = pd.DataFrame({"pu_zone_id": pu, "do_zone_id": do, "pu_hour": hours, "pu_dow": dow, "month": day.month,
                      "is_weekend": int(dow in (0, 6)), "is_holiday": int(day in NY_HOLIDAYS),
                      "is_airport": int(a.is_airport or b.is_airport), "touches_cbd": int(a.in_cbd or b.in_cbd),
                      "post_cp": int(day >= dt.date(2025, 1, 5)), "pu_x": a.x_mi, "pu_y": a.y_mi, "do_x": b.x_mi,
                      "do_y": b.y_mi, "centroid_miles": np.hypot(a.x_mi - b.x_mi, a.y_mi - b.y_mi),
                      "same_zone": int(pu == do), "passengers": 1})
    for col in ["pu_zone_id", "do_zone_id"]:
        f[col] = f[col].astype("category")                         # LightGBM maps these to its stored categories
    return f


def predict(f):
    dur, fare, tip = booster("duration"), booster("fare"), booster("tip_pct")
    minutes = np.exp(dur.predict(f[dur.feature_name()]))           # duration model is trained on log minutes
    f = f.assign(fare_amount=fare.predict(f[fare.feature_name()]).clip(min=3))
    tip_pct = tip.predict(f[tip.feature_name()]).clip(0, 100)
    return minutes, f.fare_amount.to_numpy(), tip_pct


day_rows = features(list(range(24)))
minutes, fare, tip_pct = predict(day_rows)
h = t.hour
k = st.columns(4)
k[0].metric("Trip time", f"{minutes[h]:.0f} min")
k[1].metric("Metered fare", f"${fare[h]:.2f}")
k[2].metric(f"Tip on a card ({tip_pct[h]:.0f}% of fare)", f"${fare[h] * tip_pct[h] / 100:.2f}")
k[3].metric("Straight-line distance", f"{day_rows.centroid_miles.iloc[0]:.1f} mi")

m = metrics()["models"]
mae = {w: next(v["model_MAE"] for k, v in m.items() if w in k) for w in ("Duration", "Fare")}   # match by name, whatever the prefix
st.caption(f"Typical error on unseen months: ±{mae['Duration']:.1f} min, "
           f"±${mae['Fare']:.2f} fare. Fare excludes tolls and surcharges.")

plan = pd.DataFrame({"hour": range(24), "minutes": minutes})
fig = px.line(plan, x="hour", y="minutes", markers=True, color_discrete_sequence=[C[0]],
              title=f"Predicted trip time by pickup hour on {day:%a %b %-d}")
fig.add_scatter(x=[h], y=[minutes[h]], mode="markers", marker=dict(size=13, color=C[1]), name="Your pickup time")
fig.update_xaxes(tickvals=list(range(0, 24, 3)), ticktext=[f"{x}:00" for x in range(0, 24, 3)])
fig.update_yaxes(title="Minutes", rangemode="tozero")
st.plotly_chart(style(fig, 340))
