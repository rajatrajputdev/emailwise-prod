import streamlit as st
import smtplib
from email.message import EmailMessage
from openai import AzureOpenAI
import json
import re

# === Load Config from Streamlit Secrets ===
api_key = st.secrets["openai"]["api_key"]
endpoint = st.secrets["openai"]["endpoint"]
api_version = st.secrets["openai"]["api_version"]
deployment_name = st.secrets["openai"]["deployment"]

email_address = st.secrets["email"]["address"]
email_password = st.secrets["email"]["password"]
smtp_server = st.secrets["email"]["smtp_server"]
smtp_port = st.secrets["email"]["smtp_port"]

# === Initialize Azure OpenAI Client ===
client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint,
)

# === Helper Functions ===
def build_mcp_prompt(task):
    return {
        "version": "1.0",
        "context": {
            "role": "email-assistant",
            "memory": [],
            "tools": ["send_email"]
        },
        "task": task
    }

def generate_email(mcp_prompt):
    system_prompt = (
        "You are a professional assistant. Using the provided MCP context, generate a concise, polite email."
    )
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(mcp_prompt)}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content

def send_email(to, subject, body):
    msg = EmailMessage()
    msg['From'] = email_address
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
        smtp.login(email_address, email_password)
        smtp.send_message(msg)

# === Streamlit App State Initialization ===
if "email_generated" not in st.session_state:
    st.session_state.email_generated = False
if "recipient" not in st.session_state:
    st.session_state.recipient = ""
if "subject" not in st.session_state:
    st.session_state.subject = ""
if "body" not in st.session_state:
    st.session_state.body = ""

# === UI ===
st.set_page_config(page_title="Email Assistant", page_icon="📧", layout="centered")
st.title("📧 AI Email Assistant")
st.info(f"📤 Emails will be sent from: **{email_address}**")

with st.form("generate_form"):
    task_description = st.text_area("✏️ Task Description (include email recipient)", height=150)
    generate_clicked = st.form_submit_button("Generate Email")

    if generate_clicked:
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", task_description)
        if not email_match:
            st.error("❌ No valid email address found in the task description.")
        else:
            recipient = email_match.group(0)
            with st.spinner("🧠 Generating email..."):
                try:
                    mcp = build_mcp_prompt(task_description)
                    email_content = generate_email(mcp)

                    if not email_content.strip().lower().startswith("subject:"):
                        st.error("⚠️ Unexpected response format from the model.")
                    else:
                        subject_line, body = email_content.split('\n', 1)
                        subject = subject_line.replace("Subject:", "").strip()

                        # Store in session state
                        st.session_state.email_generated = True
                        st.session_state.recipient = recipient
                        st.session_state.subject = subject
                        st.session_state.body = body.strip()
                except Exception as e:
                    st.error(f"⚠️ Error during generation: {e}")

# === Show Generated Email ===
if st.session_state.email_generated:
    st.subheader("📨 Email Preview")
    st.markdown(f"**To:** `{st.session_state.recipient}`")
    st.markdown(f"**Subject:** `{st.session_state.subject}`")
    st.text_area("Body", value=st.session_state.body, height=200, disabled=True)

    if st.button("✉️ Send Email"):
        with st.spinner("📤 Sending email..."):
            try:
                send_email(st.session_state.recipient, st.session_state.subject, st.session_state.body)
                st.success(f"✅ Email successfully sent to **{st.session_state.recipient}**!")

                # Reset state
                st.session_state.email_generated = False
            except smtplib.SMTPAuthenticationError:
                st.error("🔒 Authentication failed — check your email/password or app password.")
            except Exception as send_error:
                st.error(f"❌ Failed to send email: {send_error}")
    # st.markdown("---")
    # st.markdown("Made with ❤️ by [Your Name](https://yourwebsite.com)")