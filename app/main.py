import os
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
# absolute path: page_icon is resolved against the working directory, which differs between hosts
st.set_page_config(page_title="Beemer · Precision research for India tech", page_icon=os.path.join(HERE, "static", "beemer-logo.svg"), layout="wide", initial_sidebar_state="expanded")
import beemer as B

B.setup("Beemer")
pages = [
    st.Page("views/cockpit.py", title="Cockpit", default=True),
    st.Page("views/screener.py", title="Screener", url_path="screener"),
    st.Page("views/company.py", title="Company", url_path="company"),
    st.Page("views/learn.py", title="Academy", url_path="learn"),
]
nav = st.navigation(pages)
B.sidebar_footer()
nav.run()
