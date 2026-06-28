import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json

def init_firebase():
    """
    Инициализация Firebase с поддержкой:
    - Секретов Streamlit Cloud (разные названия)
    - Локального файла serviceAccountKey.json
    - Переменных окружения
    """
    
    # Проверяем, есть ли уже инициализированное приложение
    if firebase_admin._apps:
        return firebase_admin.get_app()
    
    try:
        # Список возможных названий секретов (проверяем все)
        secret_names = ['firebase_key', 'FIREBASE_KEY', 'firebase-key']
        firebase_creds = None
        used_secret_name = None
        
        # Пробуем получить ключ из секретов Streamlit
        for name in secret_names:
            if hasattr(st, 'secrets') and name in st.secrets:
                firebase_creds = st.secrets[name]
                used_secret_name = name
                break
        
        if firebase_creds:
            st.info(f"🔑 Использую секрет: {used_secret_name}")
            
            # Если секрет - словарь
            if isinstance(firebase_creds, dict):
                cred = credentials.Certificate(firebase_creds)
            # Если секрет - JSON строка
            elif isinstance(firebase_creds, str):
                try:
                    cred_dict = json.loads(firebase_creds)
                    cred = credentials.Certificate(cred_dict)
                except json.JSONDecodeError:
                    st.error("❌ Ошибка: секрет не является валидным JSON")
                    st.stop()
            else:
                st.error(f"❌ Неподдерживаемый тип секрета: {type(firebase_creds)}")
                st.stop()
                
        else:
            # Пробуем локальный файл (для разработки)
            st.info("🔍 Пробую найти локальный файл serviceAccountKey.json...")
            
            # Проверяем несколько возможных путей
            possible_paths = [
                "serviceAccountKey.json",
                os.path.join(os.getcwd(), "serviceAccountKey.json"),
                os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            ]
            
            key_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    key_path = path
                    break
            
            if key_path:
                st.info(f"🔑 Использую локальный файл: {os.path.basename(key_path)}")
                cred = credentials.Certificate(key_path)
            else:
                # Показываем подробную информацию об ошибке
                st.error("❌ Ошибка: не найден ключ Firebase!")
                st.error(f"📁 Текущая директория: {os.getcwd()}")
                st.info("💡 Решения:")
                st.info("  1. Для локальной разработки: поместите serviceAccountKey.json в корень проекта")
                st.info("  2. Для Streamlit Cloud: добавьте секрет 'firebase_key' в настройках")
                st.info("  3. Или используйте переменную окружения FIREBASE_KEY")
                st.stop()
        
        # Инициализируем Firebase
        firebase_admin.initialize_app(cred)
        st.success("✅ Firebase успешно подключен!")
        return firebase_admin.get_app()
        
    except Exception as e:
        st.error(f"❌ Ошибка инициализации Firebase: {e}")
        st.error("💡 Проверьте:")
        st.error("  1. Файл serviceAccountKey.json лежит в корне проекта")
        st.error("  2. Для Streamlit Cloud добавлен секрет 'firebase_key'")
        st.error("  3. Ключ Firebase действителен (не истёк)")
        st.stop()

# Инициализация Firebase
init_firebase()
db = firestore.client()

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

with st.form("survey_form"):
    st.subheader("👤 О вас")

    age = st.number_input(
        "Ваш возраст",
        min_value=14,
        max_value=80,
        step=1,
        help="Укажите ваш возраст от 14 до 80 лет"
    )
    
    gender = st.radio(
        "Пол",
        ["Мужской", "Женский", "Предпочитаю не указывать"]
    )

    st.subheader("📌 Отношение к анонимным отзывам")

    trust = st.slider(
        "Насколько вы доверяете анонимным отзывам?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 — совсем не доверяю, 10 — полностью доверяю"
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

    comment = st.text_area(
        "Дополнительные комментарии или примеры",
        placeholder="Расскажите о вашем опыте с анонимными отзывами..."
    )

    submitted = st.form_submit_button("📨 Отправить ответ")

if submitted:
    # Проверка обязательных полей
    if age < 14 or age > 80:
        st.warning("⚠️ Пожалуйста, укажите корректный возраст (14-80)")
    else:
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
            st.balloons()  # Маленький бонус 🎈
        except Exception as e:
            st.error(f"❌ Ошибка сохранения: {e}")
            st.info("💡 Попробуйте ещё раз или проверьте подключение к Firebase")

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

                # Очистка данных
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                st.subheader("📋 Сводка по данным")
                st.write(f"**Всего ответов:** {len(df)}")
                st.dataframe(df.head(10))

                # 1. Распределение доверия
                st.subheader("📊 Уровень доверия к анонимным отзывам")
                fig1 = px.histogram(
                    df,
                    x="trust",
                    nbins=10,
                    title="Распределение доверия (1–10)",
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
                    st.metric("Средний уровень доверия", f"{df['trust'].mean():.1f}/10")
                with col3:
                    st.metric("Всего ответов", len(df))

        except Exception as e:
            st.error(f"❌ Ошибка загрузки данных: {e}")
            st.info("💡 Проверьте подключение к Firebase и наличие данных")