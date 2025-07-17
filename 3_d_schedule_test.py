import streamlit as st
import plotly.graph_objects as go
import calendar
from datetime import datetime, date
import jpholiday
from collections import defaultdict

st.title("3Dスケジュール：年・月・週単位表示切替")

# 初期人物リスト
if "custom_people" not in st.session_state:
    st.session_state.custom_people = ["はると", "ゆうたろう", "あきひと"]

# 表示対象の人物リスト（フィルター用）
if "selected_people" not in st.session_state:
    st.session_state.selected_people = st.session_state.custom_people.copy()

# 人物追加フォーム
with st.form("add_person"):
    st.subheader("人物を追加")
    new_person = st.text_input("新しい人物名を入力", "")
    if st.form_submit_button("追加") and new_person and new_person not in st.session_state.custom_people:
        st.session_state.custom_people.append(new_person)
        st.session_state.selected_people.append(new_person)

# 表示対象の人物選択
st.subheader("表示する人物を選択")
st.session_state.selected_people = st.multiselect(
    "表示したい人物を選んでください",
    st.session_state.custom_people,
    default=st.session_state.selected_people
)

# イベント保存用リスト
if "user_events" not in st.session_state:
    st.session_state.user_events = []

# イベント追加フォーム
with st.form("new_event"):
    st.subheader("予定を追加")
    name = st.selectbox("人物", st.session_state.custom_people)
    year = st.number_input("年", 2000, 2100, datetime.now().year)
    month = st.number_input("月 (1~12)", 1, 12, datetime.now().month)
    day = st.number_input("日付 (1~31)", 1, 31, datetime.now().day)
    start = st.number_input("開始時刻 (0~23)", 0, 23, 9)
    end = st.number_input("終了時刻 (1~24)", 1, 24, 10)
    title = st.text_input("予定タイトル", "ミーティング")
    place = st.text_input("場所", "会議室A")
    note = st.text_input("備考", "")
    if st.form_submit_button("追加"):
        weekday = calendar.weekday(year, month, day)
        st.session_state.user_events.append((year, month, day, start, end, name, title, place, note, weekday))

# イベント削除
if st.session_state.user_events:
    st.subheader("追加した予定の削除")
    for i, e in enumerate(st.session_state.user_events):
        label = f"{e[0]}年{e[1]}月{e[2]}日 {e[3]}:00~{e[4]}:00 {e[5]}『{e[6]}』"
        if st.button(f"削除：{label}", key=f"del_{i}"):
            st.session_state.user_events.pop(i)
            st.experimental_rerun()

# グラフ描画条件
if not st.session_state.user_events:
    st.info("まずイベントを1件以上追加してください。")
    st.stop()

# 年月週選択
events = st.session_state.user_events
years = sorted(set(e[0] for e in events))
selected_year = st.selectbox("表示する年を選んでください", years)
months = sorted(set(e[1] for e in events if e[0] == selected_year))
selected_month = st.selectbox("表示する月を選んでください", months)

month_calendar = calendar.Calendar(firstweekday=0).monthdayscalendar(selected_year, selected_month)
week_ranges = {"全体": (1, max(day for week in month_calendar for day in week if day != 0))}
for idx, week in enumerate(month_calendar):
    valid_days = [d for d in week if d != 0]
    if valid_days:
        start, end = valid_days[0], valid_days[-1]
        week_ranges[f"第{idx+1}週 ({start}~{end}日)"] = (start, end)

selected_week = st.selectbox("表示する週を選んでください", list(week_ranges))
start_day, end_day = week_ranges[selected_week]

# イベント抽出
filtered = [e for e in events if e[0] == selected_year and e[1] == selected_month and start_day <= e[2] <= end_day and e[5] in st.session_state.selected_people]
people = st.session_state.selected_people
person_y = {name: i / max(1, len(people) - 1) for i, name in enumerate(people)}
colors = {name: f"hsl({(i * 360) // max(1,len(people))},70%,60%)" for i, name in enumerate(people)}
day_names = ["月", "火", "水", "木", "金", "土", "日"]

fig = go.Figure()

# イベント描画
for e in filtered:
    y_val = person_y[e[5]]
    color = "skyblue" if jpholiday.is_holiday(date(e[0], e[1], e[2])) else colors[e[5]]
    weekday_str = day_names[e[9]]
    hovertext = f"<b>{e[6]}</b><br>人物: {e[5]}<br>日付: {e[0]}年{e[1]}月{e[2]}日（{weekday_str}）<br>時間: {e[3]}:00~{e[4]}:00<br>場所: {e[7]}<br>備考: {e[8]}"
    fig.add_trace(go.Scatter3d(
        x=[e[2], e[2]],
        y=[y_val, y_val],
        z=[e[3], e[4]],
        mode='lines',
        line=dict(color=color, width=10),
        hoverinfo='text',
        text=[hovertext]*2,
        hoverlabel=dict(font=dict(color='black',size=16)),
        showlegend=False
    ))

# 重なり描画
events_by_day = defaultdict(list)
for e in filtered:
    events_by_day[e[2]].append(e)

for day, day_events in events_by_day.items():
    for i in range(len(day_events)):
        for j in range(i + 1, len(day_events)):
            e1, e2 = day_events[i], day_events[j]
            if e1[5] != e2[5]:
                start = max(e1[3], e2[3])
                end = min(e1[4], e2[4])
                if start < end:
                    y1 = person_y[e1[5]]
                    y2 = person_y[e2[5]]
                    y_mid = (y1 + y2) / 2
                    weekday_str = day_names[e1[9]]
                    hovertext = f"<b>重なり</b><br>{e1[5]}：{e1[6]}（{e1[3]}:00~{e1[4]}:00）<br>{e2[5]}：{e2[6]}（{e2[3]}:00~{e2[4]}:00）<br>重複時間：{start}:00~{end}:00<br>日付：{e1[0]}年{e1[1]}月{e1[2]}日（{weekday_str}）"
                    fig.add_trace(go.Scatter3d(
                        x=[e1[2], e1[2]],
                        y=[y_mid, y_mid],
                        z=[start, end],
                        mode='lines',
                        line=dict(color='#FF4136', width=15),
                        hoverinfo='text',
                        text=[hovertext]*2,
                        hoverlabel=dict(font=dict(color='black',size=16)),
                        showlegend=False
                    ))

# レイアウト
fig.update_layout(
    scene=dict(
        xaxis=dict(title=dict(text='日付', font=dict(color='black')), range=[end_day, start_day], dtick=1, tickfont=dict(color='black')),
        yaxis=dict(title=dict(text='人物', font=dict(color='black')), tickvals=list(person_y.values()), ticktext=people, tickfont=dict(color='black',size=14)),
        zaxis=dict(title=dict(text='時間', font=dict(color='black')), range=[24, 0], dtick=4, tickfont=dict(color='black')),
    ),
    width=900,
    height=700,
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)
