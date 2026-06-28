import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json

# -------------------------------
# 1. ИНИЦИАЛИЗАЦИЯ FIREBASE (с поддержкой secrets.toml)
# -------------------------------

def init_firebase():
    """Инициализация Firebase с поддержкой secrets.toml и локального файла"""
    
    # Проверяем, есть ли уже инициализированное приложение
    if firebase_admin._apps:
        return firebase_admin.get_app()
    
    try:
        # 1. Пробуем получить ключ из secrets.toml (Streamlit Cloud или локально)
        if hasattr(st, 'secrets') and 'FIREBASE_KEY' in st.secrets:
            st.info("🔑 Использую ключ из secrets.toml")
            firebase_creds = st.secrets["FIREBASE_KEY"]
            
            # Если секрет - словарь
            if isinstance(firebase_creds, dict):
                cred = credentials.Certificate(firebase_creds)
            # Если секрет - JSON строка
            elif isinstance(firebase_creds, str):
                cred_dict = json.loads(firebase_creds)
                cred = credentials.Certificate(cred_dict)
            else:
                st.error("❌ Неподдерживаемый тип секрета")
                st.stop()
                
        else:
            # 2. Пробуем локальный файл (для разработки)
            key_path = os.getenv("FIREBASE_KEY", "serviceAccountKey.json")
            
            if os.path.exists(key_path):
                st.info(f"🔑 Использую локальный файл: {key_path}")
                cred = credentials.Certificate(key_path)
            else:
                st.error("❌ Ошибка: Ключ Firebase не найден!")
                st.error("💡 Для локальной разработки: поместите serviceAccountKey.json в корень проекта")
                st.error("💡 Для Streamlit Cloud: добавьте секрет 'FIREBASE_KEY' в .streamlit/secrets.toml")
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
# 2. НАСТРОЙКА СТРАНИЦЫ
# -------------------------------

st.set_page_config(
    page_title="Survey: Anonymous Reviews",
    layout="wide"
)

st.title("📝 Single-Page Survey: Anonymous Reviews")
st.markdown(
    "**Topic:** Attitude towards anonymous reviews on the internet. "
    "Fill out the form. Data is saved to the cloud."
)

# -------------------------------
# 3. ФОРМА ОПРОСА
# -------------------------------

with st.form("survey"):
    col1, col2 = st.columns(2)

    with col1:
        age = st.number_input("Your age", min_value=14, max_value=80, step=1)
        gender = st.radio("Gender", ["Male", "Female", "Prefer not to say"])
        trust = st.slider("Trust in anonymous reviews (1-10)", 1, 10, 5)

    with col2:
        influence = st.radio(
            "Do anonymous reviews influence your decisions?",
            ["Yes, always", "Sometimes", "Rarely", "Never"]
        )
        faced_fake = st.radio(
            "Have you encountered fake anonymous reviews?",
            ["Yes, often", "Yes, sometimes", "Rarely", "Never"]
        )
        moderation = st.selectbox(
            "Need for moderation of anonymous reviews?",
            ["Mandatory", "Desirable", "Not necessary", "Hard to say"]
        )

    platforms = st.multiselect(
        "Platforms where you read reviews:",
        ["Yandex.Market", "Ozon", "Wildberries", "Google Maps", "2GIS", "Otzovik", "Other"]
    )

    comment = st.text_area("Additional comments or examples")

    submit = st.form_submit_button("Submit")

# -------------------------------
# 4. СОХРАНЕНИЕ ДАННЫХ
# -------------------------------

if submit:
    if not platforms:
        st.warning("Please select at least one platform!")
    else:
        record = {
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
            db.collection("responses_46").add(record)
            st.success("Response saved! Thank you!")
            st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

# -------------------------------
# 5. АНАЛИТИКА
# -------------------------------

st.markdown("---")

if st.checkbox("Analytics Dashboard (Instructor View)"):
    try:
        docs = db.collection("responses_46").stream()
        data = [doc.to_dict() for doc in docs]

        if not data:
            st.info("No responses yet.")
        else:
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            st.subheader("Data Summary")
            st.dataframe(df.head(10))

            # 1. Доверие к отзывам
            st.subheader("Trust Distribution")
            fig1 = px.histogram(
                df,
                x="trust",
                nbins=10,
                title="Trust in Anonymous Reviews (1-10)",
                labels={"trust": "Trust Level"}
            )
            st.plotly_chart(fig1, use_container_width=True)

            # 2. Влияние отзывов
            st.subheader("Influence of Reviews on Decisions")
            influence_counts = df["influence"].value_counts().reset_index()
            influence_counts.columns = ["Influence", "Count"]
            fig2 = px.bar(
                influence_counts,
                x="Influence",
                y="Count",
                title="Impact of Anonymous Reviews",
                color="Influence"
            )
            st.plotly_chart(fig2, use_container_width=True)

            # 3. Опыт встречи с фейками
            st.subheader("Experience with Fake Reviews")
            fake_counts = df["faced_fake"].value_counts().reset_index()
            fake_counts.columns = ["Experience", "Count"]
            fig3 = px.pie(
                fake_counts,
                names="Experience",
                values="Count",
                title="Encounters with Fake Reviews"
            )
            st.plotly_chart(fig3, use_container_width=True)

            # 4. Отношение к модерации
            st.subheader("Attitude to Moderation")
            mod_counts = df["moderation"].value_counts().reset_index()
            mod_counts.columns = ["Moderation", "Count"]
            fig4 = px.bar(
                mod_counts,
                x="Moderation",
                y="Count",
                title="Need for Moderation",
                color="Moderation"
            )
            st.plotly_chart(fig4, use_container_width=True)

            # 5. Популярные платформы
            st.subheader("Popular Platforms for Reviews")
            platforms_list = df["platforms"].explode().value_counts().reset_index()
            platforms_list.columns = ["Platform", "Count"]
            fig5 = px.bar(
                platforms_list,
                x="Platform",
                y="Count",
                title="Top Platforms for Reading Reviews",
                color="Platform"
            )
            st.plotly_chart(fig5, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading data: {e}")