import os
import io
import time
import zipfile
import traceback
import streamlit as st
from openai import OpenAI
from markitdown import (
    MarkItDown,
    StreamInfo,
    UnsupportedFormatException,
    FileConversionException
)

# ---------------------------------------------------------
# Page Configurations & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="MarkItDown Studio",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium custom CSS styling
st.markdown("""
<style>
/* Typography & Clean modern look */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], [class*="st-"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

h1, h2, h3, h4 {
    font-family: 'Outfit', sans-serif;
}

/* Gradient Title */
.main-title {
    background: linear-gradient(135deg, #8A2BE2 0%, #A076F9 50%, #00F2FE 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.8rem !important;
    text-align: center;
    margin-bottom: 0.2rem;
    margin-top: -1rem;
}

.subtitle {
    text-align: center;
    color: #8A99AD;
    font-size: 1.1rem;
    margin-bottom: 2rem;
    font-weight: 300;
}

/* Premium Card / Container Style */
.glass-card {
    background: rgba(255, 255, 255, 0.02);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

/* Metrics Section */
.metrics-row {
    display: flex;
    justify-content: space-around;
    align-items: center;
    background: rgba(160, 118, 249, 0.05);
    border: 1px solid rgba(160, 118, 249, 0.15);
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
}

.metric-box {
    text-align: center;
    flex: 1;
}

.metric-num {
    font-size: 1.5rem;
    font-weight: 700;
    color: #00F2FE;
}

.metric-label {
    font-size: 0.75rem;
    color: #8A99AD;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.2rem;
}

/* Action button glow effects */
.stButton>button {
    background: linear-gradient(135deg, #A076F9 0%, #6F38C5 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(160, 118, 249, 0.2) !important;
}

.stButton>button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(160, 118, 249, 0.3) !important;
}

/* Tab Active Accent colors */
div[data-baseweb="tab-list"] {
    background-color: transparent;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 1.5rem;
}

button[data-baseweb="tab"] {
    font-family: 'Outfit', sans-serif;
    color: #8A99AD !important;
    font-size: 1rem !important;
    padding: 0.8rem 1.5rem !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #00F2FE !important;
    border-bottom-color: #00F2FE !important;
    font-weight: 600 !important;
}

.success-banner {
    background: rgba(46, 213, 115, 0.1);
    border: 1px solid rgba(46, 213, 115, 0.2);
    border-radius: 8px;
    padding: 0.75rem;
    color: #2ed573;
    font-weight: 500;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "results" not in st.session_state:
    st.session_state.results = {}
if "selected_key" not in st.session_state:
    st.session_state.selected_key = None

# ---------------------------------------------------------
# Sidebar Configurations
# ---------------------------------------------------------
st.sidebar.markdown('<div style="font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #A076F9 0%, #00F2FE 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: \'Outfit\'; margin-bottom: 1.5rem;">⚙️ Configurations</div>', unsafe_allow_html=True)

# General settings
st.sidebar.subheader("🔌 Plugins & Base")
enable_plugins = st.sidebar.checkbox("Enable 3rd-party Plugins", value=False, help="Enable extension converters loaded via entry points")

# LLM Image description options
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 LLM Enrichment (Vision & OCR)")
enable_llm = st.sidebar.checkbox("Enable LLM Descriptions", value=False, help="Use a Multimodal LLM to describe images and extract text from embedded pictures.")

openai_api_key = ""
openai_endpoint = ""
llm_model = "gpt-4o"
llm_prompt = ""

if enable_llm:
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Provide your OpenAI or compatible API key")
    openai_endpoint = st.sidebar.text_input("Custom Endpoint (Optional)", placeholder="https://api.openai.com/v1", help="Custom OpenAI-compatible base URL")
    llm_model = st.sidebar.text_input("Model Name", value="gpt-4o", help="Model identifier to use (e.g. gpt-4o, gpt-4o-mini)")
    llm_prompt = st.sidebar.text_area("Custom System Prompt (Optional)", value="", placeholder="e.g. Describe this image in detail.", help="Custom instructions passed to the LLM for describing images.")

# Azure DocIntel options
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ Azure Document Intelligence")
enable_docintel = st.sidebar.checkbox("Use Azure DocIntel", value=False, help="Use Azure AI Document Intelligence for layout analysis and high-quality PDF/Office conversions")

docintel_endpoint = ""
docintel_key = ""

if enable_docintel:
    docintel_endpoint = st.sidebar.text_input("DocIntel Endpoint", placeholder="https://<region>.api.cognitive.microsoft.com/")
    docintel_key = st.sidebar.text_input("DocIntel API Key", type="password")

# Azure Content Understanding options
st.sidebar.markdown("---")
st.sidebar.subheader("🔮 Azure Content Understanding")
enable_cu = st.sidebar.checkbox("Use Content Understanding", value=False, help="Use Azure Content Understanding for advanced multi-modal extraction (audio, video, structured YAML front matter)")

cu_endpoint = ""
cu_key = ""
cu_analyzer_id = ""

if enable_cu:
    cu_endpoint = st.sidebar.text_input("CU Endpoint", placeholder="https://<region>.api.cognitive.microsoft.com/")
    cu_key = st.sidebar.text_input("CU API Key", type="password")
    cu_analyzer_id = st.sidebar.text_input("Analyzer ID (Optional)", placeholder="prebuilt-documentSearch", help="Target analyzer ID to configure")

# ---------------------------------------------------------
# Main Page Header
# ---------------------------------------------------------
st.markdown('<div class="main-title">MarkItDown Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Convert any document, image, audio, or web URL into pristine Markdown for LLM ingestion</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# MarkItDown Initialization Function
# ---------------------------------------------------------
def get_markitdown_instance():
    kwargs = {}
    
    # Configure LLM Client if enabled
    if enable_llm:
        if not openai_api_key:
            st.warning("LLM is enabled but no OpenAI API Key was provided. Image descriptions will be skipped unless default environment variables are set.")
        else:
            client_args = {"api_key": openai_api_key}
            if openai_endpoint:
                client_args["base_url"] = openai_endpoint
            
            kwargs["llm_client"] = OpenAI(**client_args)
            kwargs["llm_model"] = llm_model
            if llm_prompt:
                kwargs["llm_prompt"] = llm_prompt

    # Configure Azure Document Intelligence
    if enable_docintel and docintel_endpoint:
        kwargs["docintel_endpoint"] = docintel_endpoint
        if docintel_key:
            kwargs["docintel_credential"] = docintel_key

    # Configure Azure Content Understanding
    if enable_cu and cu_endpoint:
        kwargs["cu_endpoint"] = cu_endpoint
        if cu_key:
            kwargs["cu_credential"] = cu_key
        if cu_analyzer_id:
            kwargs["cu_analyzer_id"] = cu_analyzer_id

    return MarkItDown(enable_plugins=enable_plugins, **kwargs)

# ---------------------------------------------------------
# Layout Tabs
# ---------------------------------------------------------
tab_file, tab_url, tab_info = st.tabs(["📁 File Converter", "🔗 URL / YouTube Converter", "ℹ️ Supported Formats"])

# Tab 1: File Converter
with tab_file:
    st.markdown('<p style="font-size: 1.1rem; font-weight: 500; margin-bottom: 0.5rem;">Upload files for conversion</p>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Choose files",
        type=None, # Allow all types, let markitdown handle them
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        st.markdown(f"<div style='margin-bottom: 1rem; color: #8A99AD;'>{len(uploaded_files)} file(s) staged.</div>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        with col1:
            convert_btn = st.button("Convert All Files", key="btn_convert_files")
        
        if convert_btn:
            md = get_markitdown_instance()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Reset results for this batch
            st.session_state.results = {}
            
            for idx, uploaded_file in enumerate(uploaded_files):
                filename = uploaded_file.name
                status_text.text(f"Converting {filename}...")
                start_time = time.time()
                
                try:
                    # Get extension
                    file_ext = os.path.splitext(filename)[1].lower()
                    stream_info = StreamInfo(
                        filename=filename,
                        extension=file_ext
                    )
                    
                    # Run conversion on stream
                    uploaded_file.seek(0)
                    conversion_result = md.convert(uploaded_file, stream_info=stream_info)
                    duration = time.time() - start_time
                    
                    # Store results
                    st.session_state.results[filename] = {
                        "content": conversion_result.text_content,
                        "status": "success",
                        "size": len(uploaded_file.getvalue()),
                        "duration": duration,
                        "char_count": len(conversion_result.text_content),
                        "word_count": len(conversion_result.text_content.split())
                    }
                except Exception as e:
                    duration = time.time() - start_time
                    err_msg = traceback.format_exc()
                    st.session_state.results[filename] = {
                        "status": "error",
                        "error_msg": str(e),
                        "trace": err_msg,
                        "duration": duration
                    }
                
                # Update progress
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            status_text.empty()
            progress_bar.empty()
            st.toast("Batch conversion complete!", icon="✅")

# Tab 2: URL Converter
with tab_url:
    st.markdown('<p style="font-size: 1.1rem; font-weight: 500; margin-bottom: 0.5rem;">Enter a web URL, RSS feed, or YouTube video link</p>', unsafe_allow_html=True)
    target_url = st.text_input("Target URL", placeholder="https://example.com/document.pdf or https://www.youtube.com/watch?v=...")
    
    if target_url:
        st.markdown("")
        col_u1, col_u2 = st.columns([1, 4])
        with col_u1:
            convert_url_btn = st.button("Convert URL", key="btn_convert_url")
            
        if convert_url_btn:
            md = get_markitdown_instance()
            start_time = time.time()
            st.session_state.results = {} # Reset
            
            with st.spinner("Fetching and converting URL..."):
                try:
                    conversion_result = md.convert(target_url)
                    duration = time.time() - start_time
                    st.session_state.results[target_url] = {
                        "content": conversion_result.text_content,
                        "status": "success",
                        "size": len(conversion_result.text_content.encode("utf-8")),
                        "duration": duration,
                        "char_count": len(conversion_result.text_content),
                        "word_count": len(conversion_result.text_content.split())
                    }
                    st.toast("URL conversion complete!", icon="✅")
                except Exception as e:
                    duration = time.time() - start_time
                    err_msg = traceback.format_exc()
                    st.session_state.results[target_url] = {
                        "status": "error",
                        "error_msg": str(e),
                        "trace": err_msg,
                        "duration": duration
                    }
                    st.error(f"Failed to convert URL: {e}")

# Tab 3: Help / Info
with tab_info:
    st.markdown("""
    ### 📂 Supported File Types & Integration Methods
    
    MarkItDown converts a massive variety of inputs offline and online:
    
    | Category | Formats | Description |
    |---|---|---|
    | **Documents** | `PDF`, `DOCX`, `PPTX`, `XLSX`, `XLS`, `EPUB` | Extracts titles, headings, tables, links, and paragraphs while rendering them as semantic Markdown. |
    | **Images** | `JPG`, `PNG`, `WEBP`, `TIFF`, etc. | Generates textual descriptions (EXIF metadata) and performs OCR if LLM Vision / OCR is enabled. |
    | **Audio** | `MP3`, `WAV`, `M4A` | Transcribes audio streams to text via SpeechRecognition and extracts metadata. |
    | **Structured** | `CSV`, `JSON`, `XML` | Converts tabular and structured markup data into neatly formatted Markdown tables/lists. |
    | **Archives** | `ZIP` | Recursively opens zip contents, converts each file, and aggregates the resulting markdown. |
    | **Web / Video** | YouTube URL, RSS Feeds, Wikipedia | Automatically grabs page content, strips HTML boilerplate, or downloads video transcripts. |
    
    ---
    
    ### 💡 Pro-Tips for Production
    
    - **Vision & OCR**: When converting images or documents with embedded images (like scanned PDFs), check **Enable LLM Descriptions** and input an OpenAI API key.
    - **Azure Document Intelligence**: For industrial-scale layout parsing (multi-column tables, scanned forms), connect your Azure DocIntel service.
    - **Azure Content Understanding**: Ideal for complex multi-modal audio/video analyzes or domain-specific field parsing (invoices, calls).
    """)

# ---------------------------------------------------------
# Display Conversion Results
# ---------------------------------------------------------
if st.session_state.results:
    st.markdown("---")
    st.markdown("### 📊 Conversion Results")
    
    # Dropdown to choose which file result to inspect
    result_keys = list(st.session_state.results.keys())
    
    # If selected_key is not set or not in current keys, default to the first one
    if st.session_state.selected_key not in result_keys:
        st.session_state.selected_key = result_keys[0]
        
    selected_file = st.selectbox("Select file to preview", result_keys, index=result_keys.index(st.session_state.selected_key))
    st.session_state.selected_key = selected_file
    
    res = st.session_state.results[selected_file]
    
    if res["status"] == "success":
        # Stats Display Box
        st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-box">
                <div class="metric-num">{res['char_count']:,}</div>
                <div class="metric-label">Characters</div>
            </div>
            <div class="metric-box" style="border-left: 1px solid rgba(255,255,255,0.1); border-right: 1px solid rgba(255,255,255,0.1);">
                <div class="metric-num">{res['word_count']:,}</div>
                <div class="metric-label">Words</div>
            </div>
            <div class="metric-box" style="border-right: 1px solid rgba(255,255,255,0.1);">
                <div class="metric-num">{res['size']/1024:.2f} KB</div>
                <div class="metric-label">Input Size</div>
            </div>
            <div class="metric-box">
                <div class="metric-num">{res['duration']:.2f}s</div>
                <div class="metric-label">Conversion Time</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Download and utility actions
        col_a1, col_a2, col_a3 = st.columns([2, 2, 4])
        with col_a1:
            st.download_button(
                label="📥 Download Markdown",
                data=res["content"],
                file_name=f"{os.path.splitext(selected_file)[0]}.md",
                mime="text/markdown",
                key=f"dl_{selected_file}"
            )
            
        with col_a2:
            # Batch zip download option if multiple successes
            success_files = {k: v for k, v in st.session_state.results.items() if v["status"] == "success"}
            if len(success_files) > 1:
                # Create a zip of all files
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for fname, fdata in success_files.items():
                        base_name = os.path.splitext(fname)[0]
                        zip_file.writestr(f"{base_name}.md", fdata["content"])
                
                st.download_button(
                    label="📦 Download All as ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="markitdown_conversions.zip",
                    mime="application/zip",
                    key="dl_batch_zip"
                )
        
        # Excerpt Preview (safe, truncated to prevent page hanging)
        preview_limit = 1500
        content_len = len(res["content"])
        
        with st.expander("🔍 Preview Excerpt (First 1,500 characters only)", expanded=True):
            if content_len > preview_limit:
                preview_text = res["content"][:preview_limit] + "\n\n...\n\n[Preview truncated. Please download the file to view the full converted content.]"
            else:
                preview_text = res["content"]
            
            st.code(preview_text, language="markdown")
            
    else:
        # Error display
        st.error(f"Failed to convert: {res['error_msg']}")
        with st.expander("View Error Traceback"):
            st.code(res["trace"])
