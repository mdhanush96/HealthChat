"""
HealthChat Streamlit Frontend
Connects to the Django REST API backend running on localhost:8000
"""

import streamlit as st
import requests
import os

API_BASE = os.getenv("HEALTHCHAT_API_BASE", "http://127.0.0.1:8000/api")

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="HealthChat – AI Healthcare Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


def api_post(endpoint: str, data: dict, auth: bool = True) -> requests.Response:
    headers = auth_headers() if auth else {}
    return requests.post(f"{API_BASE}{endpoint}", json=data, headers=headers, timeout=60)


def api_get(endpoint: str) -> requests.Response:
    return requests.get(f"{API_BASE}{endpoint}", headers=auth_headers(), timeout=30)


def api_post_file(endpoint: str, file_bytes: bytes, filename: str) -> requests.Response:
    return requests.post(
        f"{API_BASE}{endpoint}",
        files={"file": (filename, file_bytes)},
        headers=auth_headers(),
        timeout=120,
    )


def refresh_access_token() -> bool:
    """Attempt to refresh JWT access token using the refresh token."""
    if not st.session_state.refresh_token:
        return False
    resp = requests.post(
        f"{API_BASE}/auth/token/refresh/",
        json={"refresh": st.session_state.refresh_token},
        timeout=15,
    )
    if resp.status_code == 200:
        st.session_state.access_token = resp.json()["access"]
        return True
    return False


# ---------------------------------------------------------------------------
# Auth pages
# ---------------------------------------------------------------------------

def page_login():
    st.title("🩺 HealthChat – AI Healthcare Assistant")
    st.markdown(
        "Welcome! Please **login** or **register** to start chatting with your AI health assistant."
    )

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            resp = requests.post(
                f"{API_BASE}/auth/login/",
                json={"username": username, "password": password},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.access_token = data["access"]
                st.session_state.refresh_token = data["refresh"]
                st.session_state.username = username
                st.session_state.messages = []
                st.session_state.conversation_id = None
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Username", key="reg_user")
            new_email = st.text_input("Email (optional)", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_pass")
            age = st.number_input("Age (optional)", min_value=1, max_value=120, value=None, step=1)
            gender = st.selectbox("Gender (optional)", ["", "male", "female", "other"])
            reg_submitted = st.form_submit_button("Register")
        if reg_submitted:
            payload = {
                "username": new_username,
                "email": new_email,
                "password": new_password,
                "age": int(age) if age else None,
                "gender": gender,
            }
            resp = requests.post(f"{API_BASE}/auth/register/", json=payload, timeout=15)
            if resp.status_code == 201:
                data = resp.json()
                st.session_state.access_token = data["access"]
                st.session_state.refresh_token = data["refresh"]
                st.session_state.username = new_username
                st.session_state.messages = []
                st.session_state.conversation_id = None
                st.success("Account created! You are now logged in.")
                st.rerun()
            else:
                errors = resp.json()
                st.error(f"Registration failed: {errors}")


# ---------------------------------------------------------------------------
# Main chat page
# ---------------------------------------------------------------------------

def page_chat():
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.divider()

        if st.button("➕ New Conversation"):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()

        # Past conversations
        st.markdown("#### 📚 Past Conversations")
        resp = api_get("/chat/conversations/")
        if resp.status_code == 200:
            convs = resp.json()
            for conv in convs[:10]:
                label = conv.get("title") or f"Conversation {conv['id']}"
                if st.button(f"💬 {label[:35]}", key=f"conv_{conv['id']}"):
                    st.session_state.conversation_id = conv["id"]
                    # Load history
                    hist_resp = api_get(f"/chat/history/{conv['id']}/")
                    if hist_resp.status_code == 200:
                        msgs = hist_resp.json().get("messages", [])
                        st.session_state.messages = [
                            {"role": m["role"], "content": m["content"]} for m in msgs
                        ]
                    st.rerun()

        st.divider()
        if st.button("📄 Upload Report", use_container_width=True):
            st.session_state["show_upload"] = True
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["access_token", "refresh_token", "username", "conversation_id", "messages"]:
                st.session_state[key] = None if key != "messages" else []
            st.rerun()

    # Upload report panel
    if st.session_state.get("show_upload"):
        _render_upload_panel()
        return

    # Chat area
    st.title("🩺 HealthChat")
    st.caption(
        "AI-powered health assistant for general guidance on common conditions. "
        "**Always consult a doctor for medical advice.**"
    )

    # Render past messages
    for msg in st.session_state.messages:
        role_label = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role_label):
            st.markdown(msg["content"])

    # User input
    user_input = st.chat_input("Describe your symptoms or ask a health question…")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("HealthChat is thinking…"):
                payload = {"message": user_input}
                if st.session_state.conversation_id:
                    payload["conversation_id"] = st.session_state.conversation_id

                resp = api_post("/chat/message/", payload)
                if resp.status_code == 401:
                    # Try token refresh
                    if refresh_access_token():
                        resp = api_post("/chat/message/", payload)

                if resp.status_code == 200:
                    data = resp.json()
                    bot_response = data["response"]
                    st.session_state.conversation_id = data["conversation_id"]

                    if data.get("is_emergency"):
                        st.error(bot_response)
                    else:
                        st.markdown(bot_response)

                    st.session_state.messages.append({"role": "bot", "content": bot_response})
                else:
                    err = "Error communicating with the server. Please try again."
                    st.error(err)
                    st.session_state.messages.append({"role": "bot", "content": err})


def _render_upload_panel():
    """Medical report upload and analysis panel."""
    st.title("📄 Upload Medical Report")
    st.markdown(
        "Upload a **PDF**, **CSV**, or **image** of your medical report. "
        "HealthChat will extract the content and provide a summary with diet advice."
    )

    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "csv", "png", "jpg", "jpeg", "tiff", "bmp"],
    )

    if uploaded:
        if st.button("Analyse Report"):
            with st.spinner("Processing your report… this may take a moment."):
                resp = api_post_file("/reports/upload/", uploaded.read(), uploaded.name)
                if resp.status_code == 201:
                    data = resp.json()
                    st.success("Report processed successfully!")
                    st.subheader("📝 Summary")
                    st.markdown(data.get("summary", "No summary available."))
                    if data.get("diet_advice"):
                        st.subheader("🥗 Diet Advice")
                        st.markdown(data["diet_advice"])
                    if data.get("extracted_text"):
                        with st.expander("📃 Extracted Text"):
                            st.text(data["extracted_text"][:2000])
                else:
                    st.error(f"Upload failed: {resp.json()}")

    if st.button("← Back to Chat"):
        st.session_state["show_upload"] = False
        st.rerun()

    st.divider()
    st.subheader("📚 Previous Reports")
    reports_resp = api_get("/reports/")
    if reports_resp.status_code == 200:
        reports = reports_resp.json()
        if not reports:
            st.info("No reports uploaded yet.")
        for r in reports:
            with st.expander(f"📋 {r['original_filename']} – {r['uploaded_at'][:10]}"):
                st.markdown(f"**Type**: {r['file_type'].upper()}")
                st.markdown(r.get("summary", ""))
                if r.get("diet_advice"):
                    st.markdown("**Diet Advice:**")
                    st.markdown(r["diet_advice"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if st.session_state.access_token is None:
        page_login()
    else:
        page_chat()


if __name__ == "__main__":
    main()
