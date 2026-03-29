# app.py
import streamlit as st
import config
import utils

st.set_page_config(page_title=config.PAGE_TITLE, page_icon=config.PAGE_ICON, layout="wide")
st.title(f"{config.PAGE_ICON} {config.PAGE_TITLE}")

@st.cache_data
def get_data():
    return utils.load_and_clean_data(config.DATA_PATH)

try:
    df = get_data()
except FileNotFoundError:
    st.error("⚠️ ملف البيانات غير موجود. تأكد من مسار الملف.")
    st.stop()

# ==========================================
# الفلاتر
# ==========================================
st.sidebar.header("⚙️ فلاتر التحكم")

# فلتر الفريق
teams = ["الكل"] + df[config.COL_TEAM].dropna().unique().tolist()
selected_team = st.sidebar.selectbox("اختر الفريق:", teams)

# فلتر اللاعب ديناميكي
if selected_team != "الكل":
    team_data = df[df[config.COL_TEAM] == selected_team]
else:
    team_data = df

players = ["الكل"] + team_data[config.COL_PLAYER].dropna().unique().tolist()
selected_player = st.sidebar.selectbox("اختر اللاعب:", players)

# ==========================================
# تطبيق الفلتر
# ==========================================
filtered_df = df.copy()

if selected_team != "الكل":
    filtered_df = filtered_df[filtered_df[config.COL_TEAM] == selected_team]

if selected_player != "الكل":
    filtered_df = filtered_df[filtered_df[config.COL_PLAYER] == selected_player]

# ==========================================
# العرض
# ==========================================
st.markdown("---")
st.subheader("📊 إحصائيات سريعة")
events, passes, shots = utils.calculate_metrics(filtered_df)

col1, col2, col3 = st.columns(3)
col1.metric("إجمالي الأحداث", events)
col2.metric("التمريرات", passes)
col3.metric("التسديدات", shots)

st.markdown("---")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("🗺️ خريطة التمريرات")
    fig_pass = utils.create_pass_map(filtered_df)
    if fig_pass:
        st.pyplot(fig_pass)
    else:
        st.warning("لا توجد تمريرات للعرض.")

with col_chart2:
    st.subheader("🔥 الخريطة الحرارية")
    fig_heat = utils.create_heatmap(filtered_df)
    if fig_heat:
        st.pyplot(fig_heat)
    else:
        st.warning("لا توجد بيانات كافية.")