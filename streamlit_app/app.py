import streamlit as st
import requests

st.set_page_config(page_title="HackRx Query System", layout="centered")

st.title("📄 Document Question Answering")

st.write("Upload a PDF or DOCX and ask questions about its contents.")

# --- Upload File ---
uploaded_file = st.file_uploader("Choose a document", type=["pdf", "docx"])

# --- Ask Questions ---
questions_input = st.text_area("Enter your questions (one per line):")
questions = [q.strip() for q in questions_input.strip().split("\n") if q.strip()]

# --- Submit Button ---
if st.button("Ask Questions"):
    if not uploaded_file:
        st.warning("Please upload a file first.")
    elif not questions:
        st.warning("Please enter at least one question.")
    else:
        with st.spinner("Processing..."):
            # Prepare request
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            data = [("questions", q) for q in questions]

            try:
                response = requests.post(
                    "http://localhost:8000/api/v1/hackrx/ask",
                    files=files,
                    data=data,
                    timeout=60
                )
                if response.status_code == 200:
                    st.success("✅ Got response!")
                    answers = response.json()
                    for i, ans in enumerate(answers["answers"]):
                        st.markdown(f"**Q{i+1}: {questions[i]}**")
                        st.write(ans)
                else:
                    st.error(f"❌ Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"💥 Exception: {e}")
