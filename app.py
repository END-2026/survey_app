import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json

# -------------------------------
# 1. Инициализация Firebase (по методичке)
# -------------------------------
def init_firebase():
    """Инициализация Firebase в соответствии с методическим пособием"""
    
    # Проверяем, есть ли уже инициализированное приложение
    if firebase_admin._apps:
        return firebase_admin.get_app()
    
    try:
        # 1. Пробуем получить ключ из секретов Streamlit (для продакшна)
        # В методичке указано: st.secrets["firebase_key"]
        if hasattr(st, 'secrets') and 'firebase_key' in st.secrets:
            st.info("🔑 Использую ключ из секретов Streamlit Cloud")
            firebase_creds = st.secrets["firebase_key"]
            
            if isinstance(firebase_creds, dict):
                cred = credentials.Certificate(firebase_creds)
            else:
                cred_dict = json.loads(firebase_creds)
                cred = credentials.Certificate(cred_dict)
                
        else:
            # 2. Пробуем локальный файл (для разработки)
            key_path = os.getenv("FIREBASE_KEY", "serviceAccountKey.json")
            
            if os.path.exists(key_path):
                st.info(f"🔑 Использую локальный файл: {key_path}")
                cred = credentials.Certificate(key_path)
            else:
                st.error("❌ Ошибка: Файл serviceAccountKey.json не найден!")
                st.error("💡 Для локальной разработки поместите файл в корень проекта.")
                st.error("💡 Для Streamlit Cloud добавьте секрет 'firebase_key' в настройках.")
                st.stop()
        
        firebase_admin.initialize_app(cred)
        st.success("✅ Firebase успешно подключен!")
        return firebase_admin.get_app()
        
    except Exception as e:
        st.error(f"❌ Ошибка инициализации Firebase: {e}")
        st.stop()

# Инициализация Firebase
init_firebase()
db = firestore.client()

# -------------------------------
# 2. Настройка страницы
# -------------------------------
st.set_page_config(
    page_title="Анонимные отзывы — Опрос",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Отношение к анонимным отзывам в сети")
st.caption(
    "Исследование о достоверности, влиянии и модерации анонимных отзывов. "
    "Данные собираются анонимно в учебных целях."
)

# -------------------------------
# 3. Форма опроса (Вариант №46)
# -------------------------------
with st.form("survey_form"):
    st.subheader("👤 О вас")

    age = st.number_input("Ваш возраст", min_value=14, max_value=80, step=1)
    gender = st.radio("Пол", ["Мужской", "Женский", "Предпочитаю не указывать"])

    st.subheader("📌 Отношение к анонимным отзывам")

    trust = st.slider(
        "Насколько вы доверяете анонимным отзывам? (1 — совсем нет, 10 — полностью доверяю)",
        1, 10, 5
    )

    influence = st.radio(
        "Влияют ли анонимные отзывы на ваше решение о покупке/выборе?",
        ["Да, всегда", "Иногда", "Редко", "Никогда"]
    )

    faced_fake = st.radio(
        "Сталкивались ли вы с заведомо ложными анонимными отзывами?",
        ["Да, часто", "Да, иногда", "Редко", "Никогда"]
    )

    moderation = st.selectbox(
        "Как вы оцениваете необходимость модерации анонимных отзывов?",
        ["Обязательна", "Желательна", "Необязательна", "Затрудняюсь ответить"]
    )

    platforms = st.multiselect(
        "На каких платформах вы чаще всего читаете отзывы?",
        ["Яндекс.Маркет", "Ozon", "Wildberries", "Google Maps", "2ГИС", "Отзовик", "Другое"]
    )

    comment = st.text_area("Дополнительные комментарии или примеры")

    submitted = st.form_submit_button("📨 Отправить ответ")

# -------------------------------
# 4. Сохранение данных в Firebase
# -------------------------------
if submitted:
    doc_data = {
        "age": int(age),
        "gender": gender,
        "trust": int(trust),
        "influence": influence,
        "faced_fake": faced_fake,
        "moderation": moderation,
        "platforms": platforms,
        "comment": comment,
        "timestamp": datetime.utcnow()
    }
    try:
        db.collection("responses_46").add(doc_data)
        st.success("✅ Спасибо! Ваш ответ сохранён.")
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {e}")

# -------------------------------
# 5. Аналитика данных (по методичке)
# -------------------------------
st.markdown("---")
if st.checkbox("📊 Показать аналитику (для преподавателя)"):
    try:
        docs = db.collection("responses_46").stream()
        data = [doc.to_dict() for doc in docs]

        if not data:
            st.info("📭 Пока нет ни одного ответа.")
        else:
            df = pd.DataFrame(data)

            # Очистка данных
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            st.subheader("📋 Сводка по данным")
            st.dataframe(df.head(10))

            # 1. Распределение доверия
            st.subheader("📊 Уровень доверия к анонимным отзывам")
            fig1 = px.histogram(
                df, x="trust", nbins=10,
                title="Распределение доверия (1–10)",
                labels={"trust": "Уровень доверия"}
            )
            st.plotly_chart(fig1, use_container_width=True)

            # 2. Влияние на решение
            st.subheader("🧭 Влияние отзывов на решение")
            influence_counts = df["influence"].value_counts().reset_index()
            influence_counts.columns = ["Влияние", "Количество"]
            fig2 = px.bar(
                influence_counts, x="Влияние", y="Количество",
                title="Влияние анонимных отзывов",
                color="Влияние"
            )
            st.plotly_chart(fig2, use_container_width=True)

            # 3. Столкновение с фейками
            st.subheader("⚠️ Столкновение с ложными отзывами")
            fake_counts = df["faced_fake"].value_counts().reset_index()
            fake_counts.columns = ["Сталкивались", "Количество"]
            fig3 = px.pie(
                fake_counts, names="Сталкивались", values="Количество",
                title="Опыт встречи с фейками"
            )
            st.plotly_chart(fig3, use_container_width=True)

            # 4. Модерация
            st.subheader("🛡️ Отношение к модерации")
            mod_counts = df["moderation"].value_counts().reset_index()
            mod_counts.columns = ["Модерация", "Количество"]
            fig4 = px.bar(
                mod_counts, x="Модерация", y="Количество",
                title="Необходимость модерации",
                color="Модерация"
            )
            st.plotly_chart(fig4, use_container_width=True)

            # 5. Популярные платформы
            st.subheader("📱 Популярные платформы для отзывов")
            platforms_list = df["platforms"].explode().value_counts().reset_index()
            platforms_list.columns = ["Платформа", "Количество"]
            fig5 = px.bar(
                platforms_list, x="Платформа", y="Количество",
                title="Платформы для чтения отзывов",
                color="Платформа"
            )
            st.plotly_chart(fig5, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных: {e}")