import streamlit as st
from src.rag import ask_rag

st.set_page_config(
    page_title="AI Healthcare Assistant",
    page_icon="🩺",
    layout="wide",
)

# ---------- Custom CSS ----------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 1.2rem;
            max-width: 1180px;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid #e5e7eb;
        }

        .app-subtitle {
            color: #6b7280;
            font-size: 0.95rem;
            margin-top: -0.25rem;
            margin-bottom: 1rem;
        }

        .empty-state {
            border: 1px dashed #d1d5db;
            background: #fafafa;
            border-radius: 16px;
            padding: 1.2rem;
            text-align: center;
            color: #6b7280;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }

        .answer-wrap {
            padding: 0.15rem 0 0.4rem 0;
        }

        .source-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 0.85rem 0.95rem;
            margin-bottom: 0.75rem;
        }

        .tiny-label {
            font-size: 0.77rem;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.2rem;
        }

        .source-summary {
            color: #4b5563;
            font-size: 0.92rem;
            margin-top: 0.35rem;
        }

        .section-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.28rem;
            line-height: 1.35;
        }

        .muted-note {
            color: #6b7280;
            font-size: 0.88rem;
        }

        div[data-testid="stChatInput"] {
            position: sticky;
            bottom: 0.4rem;
            background: rgba(255,255,255,0.92);
            padding-top: 0.5rem;
        }

        .user-row {
            display: flex;
            justify-content: flex-end;
            margin: 0.15rem 0 0.9rem 0;
        }

        .user-bubble {
            max-width: 72%;
            background: #eef2ff;
            color: #111827;
            border-radius: 18px;
            padding: 0.85rem 1rem;
            font-size: 0.98rem;
            line-height: 1.5;
            border: 1px solid #dbe4ff;
        }

        .assistant-row {
            display: flex;
            justify-content: flex-start;
            margin: 0.15rem 0 1rem 0;
        }

        .assistant-bubble {
            max-width: 100%;
            background: transparent;
            padding: 0;
            border: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Global State ----------
if "projects" not in st.session_state:
    st.session_state.projects = []

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}

if "current_project" not in st.session_state:
    st.session_state.current_project = None

if "current_chat" not in st.session_state:
    st.session_state.current_chat = None


# ---------- Helpers ----------
def create_project(project_name: str):
    clean_name = project_name.strip()

    if not clean_name:
        return "Project name cannot be empty."

    if clean_name in st.session_state.projects:
        return "Project name already exists."

    st.session_state.projects.append(clean_name)

    chat_name = f"{clean_name} chat"
    if chat_name in st.session_state.chat_sessions:
        i = 2
        base = chat_name
        while f"{base} ({i})" in st.session_state.chat_sessions:
            i += 1
        chat_name = f"{base} ({i})"

    st.session_state.chat_sessions[chat_name] = {
        "project": clean_name,
        "messages": [],
    }

    st.session_state.current_project = clean_name
    st.session_state.current_chat = chat_name

    return None


def create_new_chat(project_name=None):
    base_name = "New chat"
    existing = st.session_state.chat_sessions.keys()

    if base_name not in existing:
        new_name = base_name
    else:
        i = 2
        while f"{base_name} {i}" in existing:
            i += 1
        new_name = f"{base_name} {i}"

    st.session_state.chat_sessions[new_name] = {
        "project": project_name,
        "messages": [],
    }

    st.session_state.current_chat = new_name
    st.session_state.current_project = project_name


def get_latest_chat_for_project(project_name: str):
    for chat_name, chat_data in reversed(list(st.session_state.chat_sessions.items())):
        if chat_data["project"] == project_name:
            return chat_name
    return None


def open_project(project_name: str):
    st.session_state.current_project = project_name

    latest_chat = get_latest_chat_for_project(project_name)
    if latest_chat is not None:
        st.session_state.current_chat = latest_chat
    else:
        create_new_chat(project_name=project_name)


def get_current_messages():
    if st.session_state.current_chat is None:
        return []
    return st.session_state.chat_sessions[st.session_state.current_chat]["messages"]


def set_current_messages(messages):
    if st.session_state.current_chat is not None:
        st.session_state.chat_sessions[st.session_state.current_chat]["messages"] = messages


def auto_title_chat(first_query: str):
    current_name = st.session_state.current_chat
    if current_name is None:
        return

    if current_name.startswith("New chat"):
        short_title = first_query.strip()
        if len(short_title) > 32:
            short_title = short_title[:32] + "..."

        chat_data = st.session_state.chat_sessions.pop(current_name)

        new_name = short_title if short_title else current_name
        if new_name in st.session_state.chat_sessions:
            i = 2
            base = new_name
            while f"{base} ({i})" in st.session_state.chat_sessions:
                i += 1
            new_name = f"{base} ({i})"

        st.session_state.chat_sessions[new_name] = chat_data
        st.session_state.current_chat = new_name


def get_independent_chats():
    chats = []
    for chat_name, chat_data in reversed(list(st.session_state.chat_sessions.items())):
        if chat_data["project"] is None:
            chats.append((chat_name, chat_data))
    return chats


def get_project_chats(project_name: str):
    chats = []
    for chat_name, chat_data in reversed(list(st.session_state.chat_sessions.items())):
        if chat_data["project"] == project_name:
            chats.append((chat_name, chat_data))
    return chats


def filter_independent_chats(search_text: str):
    items = get_independent_chats()

    if not search_text:
        return items

    q = search_text.lower().strip()
    filtered = []

    for chat_name, chat_data in items:
        combined = chat_name.lower()
        for msg in chat_data["messages"]:
            combined += " " + msg.get("content", "").lower()

        if q in combined:
            filtered.append((chat_name, chat_data))

    return filtered


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🩺 Workspace")

    if st.button("✏️ New chat", use_container_width=True):
        create_new_chat(project_name=None)
        st.rerun()

    chat_search = st.text_input(
        "Search chats",
        placeholder="Search chats...",
        label_visibility="collapsed",
    )

    with st.expander("Projects", expanded=False):
        with st.form("create_project_form", clear_on_submit=True):
            new_project_name = st.text_input(
                "Project name",
                placeholder="Enter a project name...",
            )

            submitted = st.form_submit_button(
                "📁 Create project",
                use_container_width=True,
            )

            if submitted:
                error = create_project(new_project_name)
                if error:
                    st.error(error)
                else:
                    st.rerun()

        project_names = st.session_state.projects

        if project_names:
          project_options = ["— No project selected —"] + project_names

          if st.session_state.current_project in project_names:
            selected_index = project_options.index(st.session_state.current_project)
          else:
            selected_index = 0

          selected_project = st.selectbox(
            "Project history",
            project_options,
            index=selected_index,
          )

          if selected_project == "— No project selected —":
            selected_project = None

          if selected_project != st.session_state.current_project:
            if selected_project is None:
              st.session_state.current_project = None
            else:
              open_project(selected_project)
            st.rerun()

          if st.session_state.current_project is not None:
            if st.button("📂 New chat in selected project", use_container_width=True):
              create_new_chat(project_name=st.session_state.current_project)
              st.rerun()

            st.markdown("### Project chats")
            project_chats = get_project_chats(st.session_state.current_project)

            if project_chats:
              for chat_name, chat_data in project_chats:
                is_current = chat_name == st.session_state.current_chat
                icon = "●" if is_current else "○"
                label = f"{icon} {chat_name}"

                if st.button(
                    label,
                    key=f"proj_chat_{chat_name}",
                    use_container_width=True,
                ):
                    st.session_state.current_chat = chat_name
                    st.session_state.current_project = st.session_state.chat_sessions[chat_name]["project"]
                    st.rerun()
            else:
              st.caption("No chats in this project yet.")
        else:
          st.caption("No projects yet.")

    st.markdown("### Recent chats")
    filtered_chats = filter_independent_chats(chat_search)

    if filtered_chats:
        for chat_name, chat_data in filtered_chats:
            is_current = chat_name == st.session_state.current_chat
            icon = "●" if is_current else "○"
            label = f"{icon} {chat_name}"

            if st.button(label, key=f"ind_chat_{chat_name}", use_container_width=True):
                st.session_state.current_chat = chat_name
                st.session_state.current_project = None
                st.rerun()
    else:
        st.caption("No independent chats found.")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🗑️ Clear", use_container_width=True):
            if st.session_state.current_chat is not None:
                st.session_state.chat_sessions[st.session_state.current_chat]["messages"] = []
                st.rerun()

    with col_b:
        if st.button("↺ Reset all", use_container_width=True):
            st.session_state.chat_sessions = {}
            st.session_state.projects = []
            st.session_state.current_project = None
            st.session_state.current_chat = None
            st.rerun()


# ---------- Header ----------
st.title("🩺 AI Healthcare Assistant")

if st.session_state.current_chat is not None:
    project_label = st.session_state.chat_sessions[st.session_state.current_chat]["project"]

    if project_label:
        subtitle = (
            f'Chat: <strong>{st.session_state.current_chat}</strong> · '
            f'Project: <strong>{project_label}</strong>'
        )
    else:
        subtitle = f'Chat: <strong>{st.session_state.current_chat}</strong>'

    st.markdown(f'<div class="app-subtitle">{subtitle}</div>', unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="app-subtitle">Open a new chat to get started.</div>',
        unsafe_allow_html=True,
    )

st.warning(
    "This tool provides educational health information only. "
    "It does not provide medical diagnosis or replace professional care."
)


# ---------- Render Helpers ----------
def render_section(title: str, content):
    if content is None or content == "":
        return

    st.markdown(f"**{title}**")

    if isinstance(content, list):
        for item in content:
            st.markdown(f"- {item}")
    else:
        st.markdown(str(content))


def render_answer_block(sections: dict, risk: str):
    st.markdown('<div class="answer-wrap">', unsafe_allow_html=True)

    if risk == "high":
        st.error(
            "This query may involve urgent symptoms. Please seek professional medical care promptly."
        )

    display_answer = sections.get("Display answer", "")
    fast_answer = sections.get("Fast answer", "")

    if display_answer:
        st.markdown(display_answer)
    elif fast_answer:
        st.markdown(fast_answer)
    else:
        render_section("Possible concerns", sections.get("Possible concerns", ""))

    with st.expander("Details", expanded=False):
        render_section("Possible concerns", sections.get("Possible concerns", ""))
        render_section("Urgency", sections.get("Urgency", ""))
        render_section("Suggested next step", sections.get("Suggested next step", ""))
        render_section("Why", sections.get("Why", ""))

        reasoning = sections.get("Reasoning", [])
        if reasoning:
            render_section("Reasoning", reasoning)

        confidence = sections.get("Confidence", None)
        if confidence is not None:
            try:
                confidence_float = float(confidence)
                st.markdown("**Confidence**")
                st.progress(max(0.0, min(confidence_float, 1.0)))
                st.caption(f"{confidence_float:.2f}")
            except Exception:
                pass

    st.markdown("</div>", unsafe_allow_html=True)


def render_sources_tab(sources: list[dict], used_fallback: bool = False):
    if used_fallback:
        st.caption("⚡ External sources used")
    else:
        st.caption("Internal sources only or no external source retrieved")

    with st.expander("🔍 Sources used", expanded=True):
        if not sources:
            st.markdown(
                '<div class="muted-note">No sources available.</div>',
                unsafe_allow_html=True,
            )
            return

        for i, doc in enumerate(sources, start=1):
            if "rerank_score" in doc:
                score_text = f"{doc['rerank_score']:.3f}"
            elif "final_score" in doc:
                score_text = f"{doc['final_score']:.3f}"
            elif "score" in doc:
                score_text = f"{doc['score']:.3f}"
            else:
                score_text = "N/A"

            retrieval_source = doc.get("retrieval_source", "unknown").capitalize()
            publisher = doc.get("source", doc.get("source_name", "unknown"))

            st.markdown(
                f"""
                <div class="source-card">
                    <div class="tiny-label">Source {i} · {retrieval_source}</div>
                    <div class="section-title">{doc.get('title', 'Untitled source')}</div>
                    <div><strong>Publisher:</strong> {publisher}</div>
                    <div><strong>Relevance score:</strong> {score_text}</div>
                    <div class="source-summary"><strong>Snippet:</strong> {doc.get('text', '')[:220]}...</div>
                    <div style="margin-top: 0.55rem;">
                        <a href="{doc.get('url', '#')}" target="_blank">Open source</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_assistant_message(msg: dict):
    st.markdown(
        """
        <div class="assistant-row">
            <div class="assistant-bubble">
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["Answer", "Sources"])

    with tab1:
        render_answer_block(
            msg.get("sections", {}),
            msg.get("risk", "normal"),
        )

    with tab2:
        render_sources_tab(
            msg.get("sources", []),
            used_fallback=msg.get("used_fallback", False),
        )

    st.markdown(
        """
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_message(content: str):
    st.markdown(
        f"""
        <div class="user-row">
            <div class="user-bubble">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- Current Chat ----------
messages = get_current_messages()

if st.session_state.current_chat is None:
    st.markdown(
        """
        <div class="empty-state">
            <strong>No chat open.</strong><br>
            Click <strong>New chat</strong> in the sidebar to get started.
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    if len(messages) == 0:
        st.markdown(
            """
            <div class="empty-state">
                <strong>No messages yet.</strong><br>
                Start a new symptom query below.
            </div>
            """,
            unsafe_allow_html=True,
        )

    for msg in messages:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            render_assistant_message(msg)


# ---------- Input ----------
query = st.chat_input("Describe your symptoms...")

if query and st.session_state.current_chat is not None:
    messages = get_current_messages()

    user_msg = {"role": "user", "content": query}
    messages.append(user_msg)
    set_current_messages(messages)

    auto_title_chat(query)
    render_user_message(query)

    with st.spinner("Thinking..."):
        result = ask_rag(query, top_k=3)

        assistant_msg = {
            "role": "assistant",
            "content": result.get("answer", ""),
            "sections": result.get("sections", {}),
            "sources": result.get("sources", []),
            "risk": result.get("risk", "normal"),
            "used_fallback": result.get("used_fallback", False),
        }

        render_assistant_message(assistant_msg)

    messages = get_current_messages()
    messages.append(assistant_msg)
    set_current_messages(messages)