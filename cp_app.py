import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ----------------------- Константи джерел даних -----------------------
# ID файлу Google Drive зі статистикою студентів
STUDENTS_FILE_ID = "1gJTkWUssnOKKlBSIxk6rQETuEaFTA9EL"

# ID файлу Google Drive зі статистикою тріалів
TRIALS_FILE_ID = "1AsIIcj-2lYQWXHfPoMWsdtA46nqUbduH"

# ID агрегованого CSV по всіх тарифах (Apps Script)
AGG_TARIFFS_FILE_ID = "18wQuwebEBRu7Io-e142dcD3L3emDeHG1"

# Файли тарифів (Google Drive IDs)
TARIFF_FILES = {
    "Full Access 0UAH": "1XoUhnsGUeVL3qwHMYJbk4mpCn3lhoEkB",
    "Full Access 250UAH": "1G60JUAk_vQVXVQnjZF9uK2VwUbYDlK6P",
    "Full Access 350UAH": "1eYubeexGVF5MKJFZIF6ZOwEfDDad1zPB",
    "Full Access 390UAH": "1xeTeJV8JvOowE8JG5I6tog3euIKvDDNj",
    "Full Access 550UAH": "1b5fMQ_5Y522zJssO_AikhkLBTfI3p_Bf",
    "Full Access 1000UAH": "1mOZsP89AhTufFvG2nSmbV6w5GSOKyGVx",
    "Full Access 1200UAH": "1M1u8AAQHFv81BNtlvi4P6llT0OO817dj",
    "Theory Only 0UAH": "1SyARqxHQzEPlK9GEuUvNV1SEFeghJ1pr",
    "Theory Only 250UAH": "1q4c0m434WK46Thei_pgkdVB5lLDnQqZz",
    "Theory Only 500UAH": "1eFhAfdSC2LOLX3tJX5BWyGM693d0ASyK",
    "Theory Only 600UAH": "1EdZRWRQxLUfKprV5GgRWjjR_Jzyc7CEh",
}

# ----------------------- Кешоване завантаження CSV -------------------
@st.cache_data(show_spinner=False)
def load_csv_from_gdrive(file_id: str) -> pd.DataFrame:
    """Завантажує CSV з Google Drive за file_id, парсить дату та повертає DataFrame."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    df = pd.read_csv(url)
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df

# ----------------------- Налаштування сторінки -----------------------
st.set_page_config(page_title="Creative Practice Dashboard", layout="wide")

# ----------------------- Сайдбар: фільтр за датою --------------------
st.sidebar.header("Фільтр за датою")

# ▶️ Плейсхолдери для меж календаря (згодом підмінимо на межі з даних)
today = pd.to_datetime(datetime.today().date())
min_date = today - pd.DateOffset(years=2)   # умовний мінімум (2 роки тому)
max_date = today                             # умовний максимум (сьогодні)

# ▶️ Попередньо задані періоди
preset_option = st.sidebar.selectbox(
    "Швидкий вибір періоду:",
    (
        "Останні 30 днів",     # за замовчуванням
        "Попередній місяць",
        "Останні 3 місяці",
        "Останні 6 місяців",
        "Останній рік",
        "Весь час"
    ),
    index=0
)

# ▶️ Обчислюємо значення за замовчуванням для календаря на основі пресету
if preset_option == "Останні 30 днів":
    end_default = max_date
    start_default = end_default - timedelta(days=30)

elif preset_option == "Попередній місяць":
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - pd.Timedelta(days=1)
    start_default = last_day_prev_month.replace(day=1)
    end_default = last_day_prev_month

elif preset_option == "Останні 3 місяці":
    end_default = max_date
    start_default = end_default - pd.DateOffset(months=3)

elif preset_option == "Останні 6 місяців":
    end_default = max_date
    start_default = end_default - pd.DateOffset(months=6)

elif preset_option == "Останній рік":
    end_default = max_date
    start_default = end_default - pd.DateOffset(years=1)

else:  # "Весь час"
    start_default = min_date
    end_default = max_date

# ▶️ Календар з попередньо заповненим періодом
start_date, end_date = st.sidebar.date_input(
    "Або оберіть вручну:",
    value=[start_default.date(), end_default.date()],
    min_value=min_date.date(),
    max_value=max_date.date()
)

# ----------------------- Права частина (контент) ---------------------
st.title("Creative Practice Dashboard")

# ----------------------- Відображення вибраного періоду -----------------------
# Нормалізуємо типи дат до pandas.Timestamp (зручно для подальшої роботи з даними)
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date)

# Перестраховка: якщо користувач випадково вибрав дати навпаки
if start_ts > end_ts:
    start_ts, end_ts = end_ts, start_ts

# ----------------------- Графік: Передплати (агрегований CSV) -----------------------
st.subheader("Передплати")

# 1) Завантажуємо вже агрегований Apps Script-ом файл
subs_df = load_csv_from_gdrive(AGG_TARIFFS_FILE_ID).copy()

# 2) Фільтр за вибраним періодом
mask = (subs_df["date"] >= start_ts) & (subs_df["date"] <= end_ts)
subs_filtered = subs_df.loc[mask].copy()

# 3) Переконуємось, що числові колонки — саме числа
for col in ["start", "new", "reactivated", "Churned Users"]:
    subs_filtered[col] = pd.to_numeric(subs_filtered[col], errors="coerce").fillna(0)

# 4) Підписи серій для легенди
plot_df = subs_filtered.rename(columns={
    "start": "Користувачі на початок",
    "new": "Нові користувачі",
    "reactivated": "Реактивовані користувачі",
    # "Churned Users" залишаємо як є
})

# 5) Лінійний графік
fig_subs = px.line(
    plot_df,
    x="date",
    y=["Користувачі на початок", "Нові користувачі", "Реактивовані користувачі", "Churned Users"],
    markers=True,
)

# 6) Легенда знизу та косметика осей
fig_subs.update_layout(
    xaxis_title=None,
    yaxis_title=None,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    ),
    legend_title_text=""
)
fig_subs.update_xaxes(tickmode="linear", tickangle=45)

# 7) Показ графіка
st.plotly_chart(fig_subs, use_container_width=True)

# ----------------------- Графік: Тріали -----------------------
st.subheader("Тріали")

# 1) Завантажуємо дані
trials_df = load_csv_from_gdrive(TRIALS_FILE_ID)

# 2) Фільтруємо за вибраним періодом
mask = (trials_df["date"] >= start_ts) & (trials_df["date"] <= end_ts)
trials_filtered = trials_df.loc[mask].copy()

# 3) Готуємо дані для графіку
chart_trial = trials_filtered[["date", "active"]].rename(columns={"active": "Тріали"})

# 4) Будуємо лінійний графік
fig_trial = px.line(
    chart_trial,
    x="date",
    y="Тріали",
    markers=True,
)

# 5) Кастомізація осей/легенди
fig_trial.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
fig_trial.update_xaxes(tickmode="linear", tickangle=45)

# 6) Лінія медіани за вибраний період
median_trials = trials_filtered["active"].median() if not trials_filtered.empty else 0
fig_trial.add_hline(
    y=median_trials,
    line_dash="dash",
    line_color="orange",
    annotation_text=f"Медіана: {int(median_trials)}",
    annotation_position="top left"
)

# 7) Відображаємо графік
st.plotly_chart(fig_trial, use_container_width=True)

# ----------------------- Графік: Студенти -----------------------
st.subheader("Студенти")

# 1) Завантажуємо дані
students_df = load_csv_from_gdrive(STUDENTS_FILE_ID)

# 2) Фільтруємо за вибраним періодом
mask = (students_df["date"] >= start_ts) & (students_df["date"] <= end_ts)
students_filtered = students_df.loc[mask].copy()

# 3) Перейменовуємо колонку для підпису на графіку
chart_stud = students_filtered[["date", "total"]].rename(columns={"total": "Студенти"})

# 4) Будуємо лінійний графік
fig_stud = px.line(
    chart_stud,
    x="date",
    y="Студенти",
    markers=True,
)

# 5) Трохи косметики
fig_stud.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
fig_stud.update_xaxes(tickmode="linear", tickangle=45)

# 6) Показуємо графік
st.plotly_chart(fig_stud, use_container_width=True)