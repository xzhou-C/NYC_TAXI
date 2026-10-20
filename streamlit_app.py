import streamlit as st

st.set_page_config(page_title="NYC Yellow Cab", page_icon="🚕", layout="wide")
pages = st.navigation([
    st.Page("app_pages/overview.py", title="Overview", icon=":material/insights:", default=True),
    st.Page("app_pages/map.py", title="Map", icon=":material/map:"),
    st.Page("app_pages/estimator.py", title="Trip estimator", icon=":material/local_taxi:"),
    st.Page("app_pages/forecast.py", title="Forecast", icon=":material/trending_up:"),
])
pages.run()
