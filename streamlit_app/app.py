import streamlit as st
import requests
import time
import json
from typing import List, Dict, Any
import base64
from datetime import datetime
import plotly.express as px
import pandas as pd
from pathlib import Path
import io
import zipfile

# Page configuration
st.set_page_config(
    page_title="LLM Query Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# LLM-powered Query Engine\nAnalyze documents with AI!"
    }
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .upload-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin: 1rem 0;
    }
    
    .question-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 0.5rem 0;
    }
    
    .answer-box {
        background-color: #f3e5f5;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #9c27b0;
        margin: 0.5rem 0;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []
if 'current_answers' not in st.session_state:
    st.session_state.current_answers = []
if 'processing_time' not in st.session_state:
    st.session_state.processing_time = 0
if 'file_info' not in st.session_state:
    st.session_state.file_info = {}

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/v1/hackrx/ask"

def check_api_health() -> bool:
    """Check if the API is accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_file_info(file) -> Dict[str, Any]:
    """Extract file information"""
    if file is not None:
        return {
            "name": file.name,
            "size": len(file.getvalue()),
            "type": file.type,
            "size_mb": round(len(file.getvalue()) / (1024 * 1024), 2)
        }
    return {}

def process_questions(questions_text: str) -> List[str]:
    """Process and validate questions"""
    if not questions_text.strip():
        return []
    
    questions = [q.strip() for q in questions_text.split(",") if q.strip()]
    # Remove duplicates while preserving order
    unique_questions = []
    for q in questions:
        if q not in unique_questions:
            unique_questions.append(q)
    
    return unique_questions

def make_api_request(file_data, filename: str, questions: List[str]) -> Dict[str, Any]:
    """Make API request with error handling and retries"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            files = {"file": (filename, file_data)}
            data = {"questions": questions}
            
            response = requests.post(
                API_ENDPOINT,
                files=files,
                data=data,
                timeout=120  # 2 minutes timeout
            )
            
            if response.ok:
                return {"success": True, "data": response.json()}
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            return {"success": False, "error": "Request timeout. The document might be too large or complex."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to API server. Please ensure the server is running."}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    return {"success": False, "error": "Max retries exceeded"}

def display_answers(questions: List[str], answers: List[str], processing_time: float):
    """Display answers in a beautiful format"""
    st.markdown("### 🎯 Analysis Results")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Questions Processed", len(questions))
    with col2:
        st.metric("Processing Time", f"{processing_time:.2f}s")
    with col3:
        st.metric("Avg. Time/Question", f"{processing_time/len(questions):.1f}s")
    with col4:
        st.metric("Success Rate", "100%")
    
    st.markdown("---")
    
    # Q&A Display
    for i, (question, answer) in enumerate(zip(questions, answers)):
        with st.container():
            # Question
            st.markdown(f"""
            <div class="question-box">
                <strong>🤔 Question {i+1}:</strong> {question}
            </div>
            """, unsafe_allow_html=True)
            
            # Answer
            st.markdown(f"""
            <div class="answer-box">
                <strong>💡 Answer:</strong><br>
                {answer}
            </div>
            """, unsafe_allow_html=True)
            
            # Add some spacing
            st.markdown("<br>", unsafe_allow_html=True)

def export_results(questions: List[str], answers: List[str], file_info: Dict) -> bytes:
    """Export results to various formats"""
    # Create a comprehensive report
    report = {
        "timestamp": datetime.now().isoformat(),
        "file_info": file_info,
        "qa_pairs": [{"question": q, "answer": a} for q, a in zip(questions, answers)],
        "summary": {
            "total_questions": len(questions),
            "processing_time": st.session_state.processing_time
        }
    }
    
    return json.dumps(report, indent=2).encode('utf-8')

# Main App Layout
st.markdown('<h1 class="main-header">🧠 LLM-powered Query Engine</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # API Status
    api_status = check_api_health()
    status_color = "🟢" if api_status else "🔴"
    status_text = "Online" if api_status else "Offline"
    st.markdown(f"**API Status:** {status_color} {status_text}")
    
    if not api_status:
        st.warning("⚠️ API server is not accessible. Please ensure the server is running on localhost:8000")
    
    st.markdown("---")
    
    # Processing History
    if st.session_state.processing_history:
        st.markdown("### 📊 Processing History")
        history_df = pd.DataFrame(st.session_state.processing_history)
        fig = px.line(history_df, x='timestamp', y='processing_time', 
                     title='Processing Time Trend')
        st.plotly_chart(fig, use_container_width=True)
    
    # Settings
    st.markdown("### 🔧 Advanced Settings")
    max_file_size = st.slider("Max File Size (MB)", 1, 100, 10)
    show_debug = st.checkbox("Show Debug Info", False)

# Main Content
col1, col2 = st.columns([2, 1])

with col1:
    # Input Type Selection
    st.markdown("### 📥 Choose Input Method")
    option = st.radio(
        "Select how you want to provide content:",
        ["📄 Upload File", "🌐 Enter URL", "📝 Paste Text"],
        horizontal=True
    )
    
    # Questions Input
    st.markdown("### ❓ Your Questions")
    questions_text = st.text_area(
        "Enter your questions (separate multiple questions with commas):",
        value="What is this document about?, Who is responsible?, Mention key dates?",
        height=100,
        help="You can ask multiple questions by separating them with commas. Be specific for better results."
    )
    
    questions_list = process_questions(questions_text)
    
    if questions_list:
        st.info(f"✅ {len(questions_list)} questions detected")
        with st.expander("Preview Questions"):
            for i, q in enumerate(questions_list, 1):
                st.write(f"{i}. {q}")
    else:
        st.warning("⚠️ Please enter at least one question")

with col2:
    # Quick Templates
    st.markdown("### 🎯 Quick Templates")
    
    template_options = {
        "📋 Document Summary": "What is this document about?, What are the main points?, Who is the target audience?",
        "📊 Data Analysis": "What are the key metrics?, What trends are visible?, What insights can be drawn?",
        "📝 Content Review": "What is the main topic?, Who are the key people mentioned?, What dates are important?",
        "🔍 Research Questions": "What is the research question?, What methodology was used?, What are the conclusions?",
        "💼 Business Analysis": "What is the business problem?, What solutions are proposed?, What are the expected outcomes?"
    }
    
    selected_template = st.selectbox("Choose a template:", ["Custom"] + list(template_options.keys()))
    
    if selected_template != "Custom":
        if st.button("📋 Apply Template"):
            st.session_state.template_questions = template_options[selected_template]
            st.rerun()
    
    if hasattr(st.session_state, 'template_questions'):
        questions_text = st.session_state.template_questions

# Content Input Section
st.markdown("---")

if option == "📄 Upload File":
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### 📁 File Upload")
    
    uploaded_file = st.file_uploader(
        "Choose a file to analyze",
        type=["pdf", "docx", "eml", "msg", "png", "jpg", "jpeg", "txt"],
        help="Supported formats: PDF, DOCX, Email files (EML, MSG), Images (PNG, JPG, JPEG), Text files"
    )
    
    if uploaded_file:
        file_info = get_file_info(uploaded_file)
        st.session_state.file_info = file_info
        
        # Display file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", file_info["name"])
        with col2:
            st.metric("File Size", f"{file_info['size_mb']} MB")
        with col3:
            st.metric("File Type", file_info["type"])
        
        # File size validation
        if file_info["size_mb"] > max_file_size:
            st.error(f"❌ File size ({file_info['size_mb']} MB) exceeds maximum allowed size ({max_file_size} MB)")
            uploaded_file = None
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process File
    if uploaded_file and questions_list and api_status:
        if st.button("🚀 Analyze Document", type="primary", use_container_width=True):
            with st.spinner("🔄 Processing your document... This may take a few minutes."):
                start_time = time.time()
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                progress_bar.progress(25)
                status_text.text("📤 Uploading file...")
                time.sleep(0.5)
                
                progress_bar.progress(50)
                status_text.text("🧠 AI is analyzing...")
                
                result = make_api_request(
                    uploaded_file.getvalue(),
                    uploaded_file.name,
                    questions_list
                )
                
                progress_bar.progress(75)
                status_text.text("📝 Generating answers...")
                time.sleep(0.5)
                
                progress_bar.progress(100)
                status_text.text("✅ Complete!")
                
                processing_time = time.time() - start_time
                st.session_state.processing_time = processing_time
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                if result["success"]:
                    answers = result["data"]["answers"]
                    st.session_state.current_answers = answers
                    
                    # Add to history
                    st.session_state.processing_history.append({
                        "timestamp": datetime.now(),
                        "file_name": uploaded_file.name,
                        "questions_count": len(questions_list),
                        "processing_time": processing_time
                    })
                    
                    # Display results
                    display_answers(questions_list, answers, processing_time)
                    
                    # Export option
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("📊 Export Results"):
                            export_data = export_results(questions_list, answers, file_info)
                            st.download_button(
                                "💾 Download JSON Report",
                                data=export_data,
                                file_name=f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                    
                    with col2:
                        if st.button("🔄 New Analysis"):
                            st.rerun()
                    
                else:
                    st.markdown(f'<div class="error-message">❌ Error: {result["error"]}</div>', 
                              unsafe_allow_html=True)

elif option == "🌐 Enter URL":
    st.markdown("### 🌐 URL Analysis")
    
    url = st.text_input(
        "Enter the URL to analyze:",
        placeholder="https://example.com/document.pdf",
        help="Enter a direct URL to a document or webpage"
    )
    
    # URL validation
    url_valid = False
    if url:
        if url.startswith(("http://", "https://")):
            url_valid = True
            st.success("✅ Valid URL format")
        else:
            st.error("❌ Please enter a valid URL starting with http:// or https://")
    
    if url_valid and questions_list and api_status:
        if st.button("🌐 Analyze URL", type="primary", use_container_width=True):
            with st.spinner("🔄 Fetching and analyzing content from URL..."):
                start_time = time.time()
                
                result = make_api_request(
                    url.encode(),
                    "url_content.txt",
                    questions_list
                )
                
                processing_time = time.time() - start_time
                st.session_state.processing_time = processing_time
                
                if result["success"]:
                    answers = result["data"]["answers"]
                    st.session_state.current_answers = answers
                    
                    # Add to history
                    st.session_state.processing_history.append({
                        "timestamp": datetime.now(),
                        "file_name": f"URL: {url[:50]}...",
                        "questions_count": len(questions_list),
                        "processing_time": processing_time
                    })
                    
                    display_answers(questions_list, answers, processing_time)
                else:
                    st.error(f"❌ Error: {result['error']}")

elif option == "📝 Paste Text":
    st.markdown("### 📝 Text Analysis")
    
    text_content = st.text_area(
        "Paste your text content here:",
        height=200,
        placeholder="Paste the text you want to analyze..."
    )
    
    if text_content and len(text_content.strip()) > 50:
        st.info(f"✅ Text length: {len(text_content)} characters")
        
        if questions_list and api_status:
            if st.button("📝 Analyze Text", type="primary", use_container_width=True):
                with st.spinner("🔄 Analyzing your text..."):
                    start_time = time.time()
                    
                    result = make_api_request(
                        text_content.encode('utf-8'),
                        "pasted_text.txt",
                        questions_list
                    )
                    
                    processing_time = time.time() - start_time
                    st.session_state.processing_time = processing_time
                    
                    if result["success"]:
                        answers = result["data"]["answers"]
                        st.session_state.current_answers = answers
                        
                        # Add to history
                        st.session_state.processing_history.append({
                            "timestamp": datetime.now(),
                            "file_name": "Pasted Text",
                            "questions_count": len(questions_list),
                            "processing_time": processing_time
                        })
                        
                        display_answers(questions_list, answers, processing_time)
                    else:
                        st.error(f"❌ Error: {result['error']}")
    elif text_content:
        st.warning("⚠️ Please enter at least 50 characters of text")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🧠 <strong>LLM-powered Query Engine</strong> | Built with Streamlit & FastAPI</p>
    <p>Analyze documents, extract insights, get answers to your questions instantly!</p>
</div>
""", unsafe_allow_html=True)

# Debug Information
if show_debug:
    with st.expander("🐛 Debug Information"):
        st.json({
            "session_state": dict(st.session_state),
            "api_status": api_status,
            "questions_count": len(questions_list),
            "current_option": option
        })