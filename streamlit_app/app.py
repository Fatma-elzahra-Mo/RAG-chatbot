"""Arabic RAG chatbot UI with image support."""

import sys
import uuid
import json
import base64
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.core.pipeline import RAGPipeline

# Frequent questions (Arabic and English)
FREQUENT_QUESTIONS = [
    "ما هو سعر باقة X الشهرية؟",
    "كيف أشترك في باقة الإنترنت؟",
    "ما هي خدمة سلفني؟",
    "What are the WE Mix packages?",
    "ما هو رقم خدمة العملاء؟",
    "كيف أفعل خدمة 5G؟",
    "What is the price of home internet?",
    "ما هي باقات WE Gold؟",
]

# RTL CSS for Arabic
RTL_CSS = """
<style>
.rtl {
    direction: rtl;
    text-align: right;
}
.stChatMessage [data-testid="stMarkdownContainer"] {
    direction: rtl;
    text-align: right;
}
.chat-image {
    max-width: 300px;
    border-radius: 8px;
    margin: 10px 0;
}
</style>
"""

st.set_page_config(page_title="WE Chatbot", page_icon="💬", layout="centered")
st.markdown(RTL_CSS, unsafe_allow_html=True)


@st.cache_resource
def load_pipeline():
    return RAGPipeline()


def encode_image(image_file) -> str:
    """Encode image to base64."""
    return base64.b64encode(image_file.read()).decode('utf-8')


def analyze_image_with_text(image_base64: str, text: str, file_type: str) -> str:
    """Analyze image using vision model via OpenRouter."""
    import requests

    # Use OpenRouter API (you already have credits there)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Error: OPENROUTER_API_KEY not set for image analysis"

    # Create prompt
    prompt = f"""You are a helpful assistant for WE Egypt telecom services.
Analyze this image and answer the user's question.
If the question is in Arabic, respond in Egyptian Arabic dialect.
If the question is in English, respond in English.

User's question: {text if text else 'ما هذه الصورة؟ / What is this image?'}

Provide a helpful response based on what you see in the image."""

    try:
        # OpenRouter API call with vision model
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "WE Arabic RAG Chatbot"
            },
            json={
                "model": "google/gemini-2.0-flash-exp:free",  # Free vision model
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{file_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
            }
        )

        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error analyzing image: {str(e)}"
    except Exception as e:
        return f"Error processing response: {str(e)}"


def handle_upload(file, pipeline):
    """Ingest uploaded file."""
    try:
        ext = file.name.split('.')[-1].lower()
        if ext == 'json':
            data = json.load(file)
            content = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else "\n".join(str(x) for x in data)
        else:
            content = file.read().decode('utf-8')

        if len(content) < 10:
            return False, "File too short"

        pipeline.ingest_documents([content], [{'source': file.name, 'title': file.name}])
        return True, f"Added: {file.name}"
    except Exception as e:
        return False, str(e)


def handle_question(question: str):
    """Process a question and get response."""
    st.session_state.messages.append({"role": "user", "content": question})
    pipeline = load_pipeline()
    result = pipeline.query(question, session_id=st.session_state.session_id, use_rag=True)
    response = result["response"]
    st.session_state.messages.append({"role": "assistant", "content": response})


def display_message(msg):
    """Display a chat message with support for images."""
    with st.chat_message(msg["role"]):
        # Display image if present
        if msg.get("image"):
            st.image(
                f"data:image/{msg.get('image_type', 'png')};base64,{msg['image']}",
                caption="Uploaded Image",
                width=300
            )
        # Display text
        if msg.get("content"):
            st.markdown(f'<div class="rtl">{msg["content"]}</div>', unsafe_allow_html=True)


def main():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "selected_question" not in st.session_state:
        st.session_state.selected_question = None
    if "pending_image" not in st.session_state:
        st.session_state.pending_image = None

    # Sidebar
    with st.sidebar:
        st.header("WE Chatbot")

        # Document Upload
        st.subheader("Add Documents")
        doc_file = st.file_uploader("Upload (txt/json/md)", type=['txt', 'json', 'md'], key="doc_upload")
        if doc_file and st.button("Add to Knowledge"):
            pipeline = load_pipeline()
            ok, msg = handle_upload(doc_file, pipeline)
            st.success(msg) if ok else st.error(msg)

        st.divider()

        # Image Upload
        st.subheader("Chat with Image")
        image_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg', 'gif', 'webp'], key="img_upload")
        if image_file:
            st.image(image_file, caption="Preview", width=200)
            if st.button("Send Image"):
                image_file.seek(0)
                image_base64 = encode_image(image_file)
                ext = image_file.name.split('.')[-1].lower()
                if ext == 'jpg':
                    ext = 'jpeg'
                st.session_state.pending_image = {
                    "base64": image_base64,
                    "type": ext,
                    "name": image_file.name
                }
                st.rerun()

        st.divider()
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.pending_image = None
            st.rerun()

    # Chat
    st.title("💬 WE Assistant")

    # Frequent Questions (only show when no messages)
    if not st.session_state.messages:
        st.markdown("**الأسئلة الشائعة / Frequent Questions:**")
        cols = st.columns(2)
        for i, question in enumerate(FREQUENT_QUESTIONS):
            col = cols[i % 2]
            if col.button(question, key=f"fq_{i}", use_container_width=True):
                st.session_state.selected_question = question
                st.rerun()

    # Handle selected frequent question
    if st.session_state.selected_question:
        question = st.session_state.selected_question
        st.session_state.selected_question = None
        with st.spinner("..."):
            handle_question(question)
        st.rerun()

    # Handle pending image
    if st.session_state.pending_image:
        img_data = st.session_state.pending_image
        st.session_state.pending_image = None

        # Add user message with image
        st.session_state.messages.append({
            "role": "user",
            "content": "📷 [Image uploaded]",
            "image": img_data["base64"],
            "image_type": img_data["type"]
        })

        # Analyze image
        with st.spinner("Analyzing image..."):
            response = analyze_image_with_text(
                img_data["base64"],
                "",  # No text question, just analyze
                img_data["type"]
            )
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
        st.rerun()

    # Display messages
    for msg in st.session_state.messages:
        display_message(msg)

    # Chat input with optional image context
    if prompt := st.chat_input("اكتب سؤالك... / Type your question..."):
        # Check if last user message had an image
        last_image = None
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user" and msg.get("image"):
                last_image = msg
                break

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(f'<div class="rtl">{prompt}</div>', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            with st.spinner("..."):
                # If recent image, use vision model
                if last_image and len(st.session_state.messages) <= 4:
                    response = analyze_image_with_text(
                        last_image["image"],
                        prompt,
                        last_image.get("image_type", "png")
                    )
                else:
                    # Use RAG pipeline
                    pipeline = load_pipeline()
                    result = pipeline.query(prompt, session_id=st.session_state.session_id, use_rag=True)
                    response = result["response"]

                st.markdown(f'<div class="rtl">{response}</div>', unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
