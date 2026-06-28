import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json

def init_firebase():
    """Инициализация Firebase с поддержкой secrets.toml и локального файла"""
    
    # Проверяем, есть ли уже инициализированное приложение
    if firebase_admin._apps:
        return firebase_admin.get_app()
    
    try:
        # 1. Пробуем получить ключ из secrets.toml (Streamlit Cloud или локально)
        if hasattr(st, 'secrets') and 'FIREBASE_KEY' in st.secrets:
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
                cred = credentials.Certificate(key_path)
            else:
                st.error("❌ Ошибка: Ключ Firebase не найден!")
                st.error("💡 Для локальной разработки: поместите serviceAccountKey.json в корень проекта")
                st.error("💡 Для Streamlit Cloud: добавьте секрет 'FIREBASE_KEY' в .streamlit/secrets.toml")
                st.stop()
        
        firebase_admin.initialize_app(cred)
        return firebase_admin.get_app()
        
    except Exception as e:
        st.error(f"❌ Ошибка инициализации Firebase: {e}")
        st.stop()

# Инициализация Firebase
init_firebase()
db = firestore.client()

st.set_page_config(
    page_title="Опрос: Анонимные отзывы",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Опрос: Отношение к анонимным отзывам в сети")
st.markdown(
    "**Тема:** Исследование достоверности, влияния и модерации анонимных отзывов. "
    "Данные собираются анонимно в учебных целях."
)

with st.form("survey"):
    st.subheader("👤 О вас")
    
    col1, col2 = st.columns(2)

    with col1:
        age = st.number_input(
            "Ваш возраст",
            min_value=14,
            max_value=80,
            step=1,
            help="Укажите ваш возраст от 14 до 80 лет"
        )
        gender = st.radio(
            "Ваш пол",
            ["Мужской", "Женский", "Предпочитаю не указывать"]
        )

    with col2:
        trust = st.slider(
            "Насколько вы доверяете анонимным отзывам?",
            min_value=1,
            max_value=10,
            value=5,
            help="1 — совсем не доверяю, 10 — полностью доверяю"
        )

    st.subheader("📌 Отношение к анонимным отзывам")

    col3, col4 = st.columns(2)

    with col3:
        influence = st.radio(
            "Влияют ли анонимные отзывы на ваше решение о покупке/выборе?",
            ["Да, всегда", "Иногда", "Редко", "Никогда"]
        )
        
        faced_fake = st.radio(
            "Сталкивались ли вы с заведомо ложными анонимными отзывами?",
            ["Да, часто", "Да, иногда", "Редко", "Никогда"]
        )

    with col4:
        moderation = st.selectbox(
            "Как вы оцениваете необходимость модерации анонимных отзывов?",
            ["Обязательна", "Желательна", "Необязательна", "Затрудняюсь ответить"]
        )

    platforms = st.multiselect(
        "На каких платформах вы чаще всего читаете отзывы?",
        ["Яндекс.Маркет", "Ozon", "Wildberries", "Google Maps", "2ГИС", "Отзовик", "Другое"]
    )

    comment = st.text_area(
        "Дополнительные комментарии или примеры",
        placeholder="Расскажите о вашем опыте с анонимными отзывами..."
    )

    submit = st.form_submit_button("📨 Отправить ответ")

if submit:
    if not platforms:
        st.warning("⚠️ Пожалуйста, выберите хотя бы одну платформу!")
    elif age < 14 or age > 80:
        st.warning("⚠️ Пожалуйста, укажите корректный возраст (14-80)")
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
            st.success("✅ Спасибо! Ваш ответ сохранён.")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Ошибка сохранения: {e}")

st.markdown("---")

if st.checkbox("📊 Показать аналитику (для преподавателя)"):
    with st.spinner("Загрузка данных..."):
        try:
            docs = db.collection("responses_46").stream()
            data = [doc.to_dict() for doc in docs]

            if not data:
                st.info("📭 Пока нет ни одного ответа.")
                st.info("Заполните форму выше, чтобы увидеть аналитику.")
            else:
                df = pd.DataFrame(data)
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                # Перевод колонок для отображения
                column_names = {
                    "age": "Возраст",
                    "gender": "Пол",
                    "trust": "Доверие",
                    "influence": "Влияние",
                    "faced_fake": "Сталкивались с фейками",
                    "moderation": "Модерация",
                    "platforms": "Платформы",
                    "comment": "Комментарий",
                    "timestamp": "Время отправки"
                }
                df_ru = df.rename(columns=column_names)

                st.subheader("📋 Сводка по данным")
                st.write(f"**Всего ответов:** {len(df)}")
                st.dataframe(df_ru.head(10), use_container_width=True)

                # 1. Распределение доверия
                st.subheader("📊 Уровень доверия к анонимным отзывам")
                fig1 = px.histogram(
                    df,
                    x="trust",
                    nbins=10,
                    title="Распределение уровня доверия (1–10)",
                    labels={"trust": "Уровень доверия", "count": "Количество респондентов"},
                    color_discrete_sequence=["#4CAF50"]
                )
                fig1.update_layout(bargap=0.1)
                st.plotly_chart(fig1, use_container_width=True)

                # 2. Влияние на решение
                st.subheader("🧭 Влияние отзывов на решение")
                influence_counts = df["influence"].value_counts().reset_index()
                influence_counts.columns = ["Влияние", "Количество"]
                fig2 = px.bar(
                    influence_counts,
                    x="Влияние",
                    y="Количество",
                    title="Влияние анонимных отзывов",
                    color="Влияние",
                    color_discrete_sequence=["#2196F3", "#FF9800", "#9E9E9E", "#F44336"]
                )
                st.plotly_chart(fig2, use_container_width=True)

                # 3. Столкновение с фейками
                st.subheader("⚠️ Столкновение с ложными отзывами")
                fake_counts = df["faced_fake"].value_counts().reset_index()
                fake_counts.columns = ["Сталкивались", "Количество"]
                fig3 = px.pie(
                    fake_counts,
                    names="Сталкивались",
                    values="Количество",
                    title="Опыт встречи с фейками",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig3, use_container_width=True)

                # 4. Модерация
                st.subheader("🛡️ Отношение к модерации")
                mod_counts = df["moderation"].value_counts().reset_index()
                mod_counts.columns = ["Модерация", "Количество"]
                fig4 = px.bar(
                    mod_counts,
                    x="Модерация",
                    y="Количество",
                    title="Необходимость модерации",
                    color="Модерация",
                    color_discrete_sequence=["#4CAF50", "#8BC34A", "#FFC107", "#FF5722"]
                )
                st.plotly_chart(fig4, use_container_width=True)

                # 5. Популярные платформы
                st.subheader("📱 Популярные платформы для отзывов")
                platforms_list = df["platforms"].explode().value_counts().reset_index()
                platforms_list.columns = ["Платформа", "Количество"]
                fig5 = px.bar(
                    platforms_list,
                    x="Платформа",
                    y="Количество",
                    title="Платформы для чтения отзывов",
                    color="Платформа",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig5, use_container_width=True)

                # 6. Дополнительная статистика
                st.subheader("📈 Дополнительная статистика")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Средний возраст", f"{df['age'].mean():.1f} лет")
                with col2:
                    st.metric("Средний уровень доверия", f"{df['trust'].mean():.1f} / 10")
                with col3:
                    st.metric("Всего ответов", len(df))

        except Exception as e:
            st.error(f"❌ Ошибка загрузки данных: {e}")