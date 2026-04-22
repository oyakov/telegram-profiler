"""Networking Brain — Панель управления Streamlit 2.0."""

import os
import httpx
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

API_BASE = os.getenv("API_BASE_URL", "http://app:8000")

# ========== Global State & DB Selection ==========
if "selected_db" not in st.session_state:
    st.session_state.selected_db = "crm"

# ========== API Helpers ==========
def api_get(path: str, params: dict | None = None):
    headers = {"X-Database": st.session_state.selected_db}
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Ошибка API (GET {path}): {e}")
        return None

def api_post(path: str, json: dict | None = None, files=None):
    headers = {"X-Database": st.session_state.selected_db}
    try:
        r = httpx.post(f"{API_BASE}{path}", json=json, files=files, headers=headers, timeout=60.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Ошибка API (POST {path}): {e}")
        return None

# ========== Page Config ==========
st.set_page_config(page_title="Networking Brain 2.0", page_icon="🧠", layout="wide")

# ========== Custom CSS ==========
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem; }
    .card { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .status-badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
    .status-active { background-color: #d1fae5; color: #065f46; }
    .status-idle { background-color: #f3f4f6; color: #374151; }
</style>
""", unsafe_allow_html=True)

# ========== Sidebar ==========
with st.sidebar:
    st.markdown('<div class="main-header">🧠 Brain 2.0</div>', unsafe_allow_html=True)
    
    # 1. Project/Folder Selection
    FOLDER_MAP = {
        "🇷🇸 Belgrade Intel": "crm",
        "💰 Crypto Universe": "crm_crypto"
    }
    
    current_idx = 1 if st.session_state.selected_db == "crm_crypto" else 0
    selected_label = st.selectbox(
        "📂 Активный проект",
        options=list(FOLDER_MAP.keys()),
        index=current_idx,
        help="Переключает базу данных и контекст всей системы."
    )
    
    new_db = FOLDER_MAP[selected_label]
    if new_db != st.session_state.selected_db:
        st.session_state.selected_db = new_db
        st.rerun()
        
    st.divider()
    
    # 2. Navigation
    page = st.radio("Навигация", [
        "📊 Дашборд",
        "📡 Трекинг",
        "📈 AI Мониторинг",
        "🔍 Поиск и AI",
        "🎯 Лиды",
        "👥 Контакты",
        "⚙️ Настройки"
    ], label_visibility="collapsed")

    st.divider()
    
    # 3. System Status (Mini)
    health = api_get("/api/stats/health") # Use system health
    if health:
        st.caption(f"Статус: {'🟢 В норме' if health.get('status') == 'healthy' else '🟡 Проверка...'}")

# ========== Utility: Header ==========
def header(title, subtitle=None):
    st.markdown(f'<div class="main-header">{title}</div>', unsafe_allow_html=True)
    if subtitle: st.write(f"**{subtitle}**")
    st.divider()

# ========== PAGES ==========

if page == "📊 Дашборд":
    header("Обзор проекта", selected_label)
    
    stats = api_get("/api/stats")
    if stats:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Контактов", stats.get("total_contacts", 0))
        m2.metric("Сообщений", stats.get("total_messages", 0))
        
        # Get channel count from tracking
        tracking = api_get("/api/tracking/channels")
        ch_count = len(tracking.get("channels", [])) if tracking else 0
        m3.metric("Каналов", ch_count)
        m4.metric("Голосовых", stats.get("total_voice_notes", 0))

        st.subheader("📈 Активность по источникам")
        by_source = stats.get("contacts_by_source", {})
        if by_source:
            df = pd.DataFrame(list(by_source.items()), columns=["Источник", "Кол-во"])
            fig = px.bar(df, x="Источник", y="Кол-во", color="Источник", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
        st.subheader("📡 Топ-10 каналов по объему данных")
        if tracking and tracking.get("channels"):
            ch_data = pd.DataFrame(tracking["channels"])
            ch_data = ch_data.sort_values("messages_count", ascending=False).head(10)
            st.table(ch_data[["title", "messages_count", "last_sync"]])

elif page == "📡 Трекинг":
    header("Управление отслеживанием", "Список каналов и статус их наполнения.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f"В этой папке отслеживается каналов: **{selected_label}**")
    with col2:
        if st.button("🔄 Синхронизировать с Telegram", use_container_width=True):
            with st.spinner("Сканирую папку в Telegram..."):
                # Use the script logic here via API or task
                api_post("/api/connectors/telegram/sync")
                st.toast("Задача на обновление списка каналов запущена")

    tracking = api_get("/api/tracking/channels")
    if tracking and tracking.get("channels"):
        channels = tracking["channels"]
        
        # Display as a table with progress
        df_ch = pd.DataFrame(channels)
        df_display = df_ch[["title", "username", "messages_count", "is_active", "type"]].copy()
        df_display.columns = ["Название", "Username", "Сообщений", "Активен", "Тип"]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Поиск новых сообществ")
        q = st.text_input("Поиск в Telegram (ключевое слово)", placeholder="Например: 'Белград'")
        if st.button("Найти новые каналы"):
            results = api_get("/api/telegram/search", params={"query": q})
            if results:
                for item in results.get("results", []):
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"**{item['title']}** ({item['participants']} чел.)")
                        c1.caption(item['about'][:150] if item['about'] else "Нет описания")
                        if c2.button("Добавить в трекинг", key=f"add_{item['id']}"):
                            api_post("/api/telegram/join", json={"chat_id": str(item['id']), "username": item['username'], "deep_sync_days": 30})
                            st.toast("Добавлено!")

elif page == "📈 AI Мониторинг":
    header("Мониторинг AI", "Аналитика использования LLM и качества экстракции.")
    
    ai_stats = api_get("/api/stats/ai-monitoring")
    if ai_stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Всего запусков", ai_stats.get("total_runs", 0))
        c2.metric("Успешность", f"{ai_stats.get('success_rate', 0):.1f}%")
        c3.metric("Затраты (est)", f"${ai_stats.get('estimated_cost_usd', 0):.4f}")
        c4.metric("Avg Latency", f"{ai_stats.get('avg_processing_time_ms', 0)}ms")
        
        st.divider()
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("📊 Использование токенов")
            token_data = pd.DataFrame({
                "Тип": ["Prompt", "Completion"],
                "Токены": [ai_stats.get("total_prompt_tokens", 0), ai_stats.get("total_completion_tokens", 0)]
            })
            fig_tokens = px.pie(token_data, values="Токены", names="Тип", hole=0.4, 
                               color_discrete_sequence=["#636EFA", "#EF553B"])
            st.plotly_chart(fig_tokens, use_container_width=True)
            
        with col_t2:
            st.subheader("📋 Последние логи экстракции")
            # We'd need a paginated log endpoint here for a real list
            st.info("Здесь будут отображаться последние 50 ошибок экстракции для отладки.")
            # For now, let's keep it simple or add an endpoint if needed

elif page == "🔍 Поиск и AI":
    header("Интеллектуальный поиск", "Поиск по всей базе с использованием AI.")
    
    t1, t2 = st.tabs(["🤖 Семантический поиск (AI)", "🔎 Поиск по словам"])
    
    with t1:
        s_query = st.text_input("Запрос на естественном языке", placeholder="Например: 'кто продает квартиры в центре' или 'специалисты по крипте'")
        if s_query:
            with st.spinner("AI анализирует смыслы..."):
                res = api_post("/api/search", json={"query": s_query, "limit": 15})
                if res:
                    col_left, col_right = st.columns([1, 2])
                    with col_left:
                        st.subheader("👥 Найденные люди")
                        for c in res.get("contacts", []):
                            with st.container(border=True):
                                st.write(f"**{c.get('first_name')} {c.get('last_name') or ''}**")
                                st.caption(f"@{c.get('telegram_username') or 'Н/Д'}")
                                st.progress(c['similarity'], text=f"Сходство {c['similarity']:.0%}")
                    with col_right:
                        st.subheader("💬 Релевантные сообщения")
                        for m in res.get("messages", []):
                            with st.chat_message("user", avatar="🧠"):
                                st.markdown(f"**{m['contact_name']}** в *{m['group_name']}*")
                                st.write(m['content'])
                                st.caption(f"{m['timestamp'][:16]} | Score: {m['similarity']:.2f}")

    with t2:
        # Standard keyword search
        kw_query = st.text_input("Ключевое слово")
        res = api_get("/api/messages/search", params={"query": kw_query, "page_size": 50}) if kw_query else None
        if res and res.get("messages"):
            st.dataframe(pd.DataFrame([
                {"Дата": m["timestamp"][:16], "Группа": m.get("group_name"), "Автор": m.get("contact_name"), "Текст": m["content"]}
                for m in res["messages"]
            ]), use_container_width=True)

elif page == "🎯 Лиды":
    header("Лиды и Рекламодатели", "Автоматически выявленные коммерческие запросы.")

    c1, c2 = st.columns([3, 1])
    min_score = c1.slider("Порог качества (Score)", 0, 100, 10)
    if c2.button("🚀 Пересчитать всё"):
        api_post("/api/leads/process")
        st.toast("Запущено")

    data = api_get("/api/leads/top", params={"min_score": min_score})
    if data and data.get("contacts"):
        for l in data["contacts"]:
            with st.expander(f"💰 {l['first_name']} | Score: {l['lead_score']}"):
                st.write(f"**Активность:** {l.get('our_channel_ratio')}% в нашем канале")
                if st.button("Посмотреть историю", key=f"btn_h_{l['id']}"):
                    hist = api_get(f"/api/leads/{l['id']}/history")
                    if hist:
                        for entry in hist.get("lead_history", []):
                            st.info(f"{entry['timestamp'][:10]} | {entry['summary']}")

elif page == "👥 Контакты":
    header("База контактов", f"Всего в проекте: {selected_label}")
    search = st.text_input("Поиск по базе")
    data = api_get("/api/contacts", params={"search": search} if search else None)
    if data:
        df = pd.DataFrame(data.get("contacts", []))
        if not df.empty:
            st.dataframe(df[["first_name", "last_name", "telegram_username", "source", "lead_score"]], use_container_width=True)
elif page == "⚙️ Настройки":
    header("Настройки проекта")
    st.warning("Внимание: Настройки применяются только к выбранному проекту.")
    settings = api_get("/api/settings")
    if settings:
        for s in settings.get("settings", []):
            with st.container():
                st.write(f"**{s['key']}**")
                val = st.text_input("Значение", value=str(s.get("raw_value", "")), key=f"input_{s['key']}", label_visibility="collapsed")
                if st.button("Сохранить", key=f"save_{s['key']}"):
                    api_put(f"/api/settings/{s['key']}", json={"value": val})
                    st.toast("Настройка сохранена")
