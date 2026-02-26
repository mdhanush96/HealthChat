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
)

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
for key, default in {
    "access_token": None,
    "refresh_token": None,
    "username": None,
    "conversation_id": None,
    "messages": [],
    "show_upload": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


def api_post(endpoint, data, auth=True):
    headers = auth_headers() if auth else {}
    return requests.post(f"{API_BASE}{endpoint}", json=data, headers=headers, timeout=60)


def api_get(endpoint):
    return requests.get(f"{API_BASE}{endpoint}", headers=auth_headers(), timeout=30)


def api_post_file(endpoint, file_bytes, filename):
    return requests.post(
        f"{API_BASE}{endpoint}",
        files={"file": (filename, file_bytes)},
        headers=auth_headers(),
        timeout=120,
    )


def refresh_access_token():
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


def safe_json_error(resp):
    try:
        return str(resp.json())
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"

# ---------------------------------------------------------------------------
# Login / Register
# ---------------------------------------------------------------------------

def page_login():
    st.title("🩺 HealthChat – AI Healthcare Assistant")

    tab1, tab2 = st.tabs(["Login", "Register"])

    # LOGIN
    with tab1:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            resp = requests.post(
                f"{API_BASE}/auth/login/",
                json={"username": username, "password": password},
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.access_token = data["access"]
                st.session_state.refresh_token = data["refresh"]
                st.session_state.username = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

    # REGISTER
    with tab2:
        with st.form("register"):
            username = st.text_input("Username", key="reg_user")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password", key="reg_pass")
            age = st.number_input("Age", min_value=1, max_value=120, step=1)
            gender = st.selectbox("Gender", ["", "male", "female", "other"])
            submitted = st.form_submit_button("Register")

        if submitted:
            payload = {
                "username": username,
                "email": email,
                "password": password,
                "age": age,
                "gender": gender,
            }
            resp = requests.post(f"{API_BASE}/auth/register/", json=payload)

            if resp.status_code == 201:
                data = resp.json()
                st.session_state.access_token = data["access"]
                st.session_state.refresh_token = data["refresh"]
                st.session_state.username = username
                st.success("Registered successfully!")
                st.rerun()
            else:
                st.error(f"Registration failed: {safe_json_error(resp)}")

# ---------------------------------------------------------------------------
# Upload Panel
# ---------------------------------------------------------------------------

def upload_panel():
    st.title("📄 Upload Medical Report")

    uploaded = st.file_uploader(
        "Upload PDF, CSV, or Image",
        type=["pdf", "csv", "png", "jpg", "jpeg"],
    )

    if uploaded:
        if st.button("Analyse Report"):
            with st.spinner("Processing..."):
                resp = api_post_file("/reports/upload/", uploaded.read(), uploaded.name)

                if resp.status_code == 201:
                    data = resp.json()
                    st.success("Report processed!")

                    st.subheader("📝 Summary")
                    st.write(data.get("summary"))

                    if data.get("diet_advice"):
                        st.subheader("🥗 Diet Advice")
                        st.write(data["diet_advice"])

                else:
                    st.error(f"Upload failed: {safe_json_error(resp)}")

    if st.button("← Back"):
        st.session_state.show_upload = False
        st.rerun()

# ---------------------------------------------------------------------------
# Chat Page
# ---------------------------------------------------------------------------

def page_chat():

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")

        if st.button("➕ New Conversation"):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()

        if st.button("📄 Upload Report"):
            st.session_state.show_upload = True
            st.rerun()

        if st.button("🚪 Logout"):
            for key in st.session_state.keys():
                st.session_state[key] = None if key != "messages" else []
            st.rerun()

    if st.session_state.show_upload:
        upload_panel()
        return

    st.title("🩺 HealthChat")

    # Show previous messages
    for msg in st.session_state.messages:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])

    user_input = st.chat_input("Describe symptoms or ask health question...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                payload = {"message": user_input}
                if st.session_state.conversation_id:
                    payload["conversation_id"] = st.session_state.conversation_id

                resp = api_post("/chat/message/", payload)

                if resp.status_code == 401:
                    if refresh_access_token():
                        resp = api_post("/chat/message/", payload)

                if resp.status_code == 200:
                    data = resp.json()
                    response = data["response"]
                    st.session_state.conversation_id = data["conversation_id"]
                    st.markdown(response)
                    st.session_state.messages.append({"role": "bot", "content": response})
                else:
                    error_msg = safe_json_error(resp)
                    st.error(error_msg)

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main():
    if st.session_state.access_token is None:
        page_login()
    else:
        page_chat()


if __name__ == "__main__":
    main()