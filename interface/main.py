import os
# CRITICAL FIX: MUST BE THE FIRST LINE 
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import tempfile
import math
import database as db
import utils

# CONFIGURATION 
st.set_page_config(page_title="OphthalmoCapture", layout="wide", page_icon="👁️")

# Change these paths to match your actual folders
CSV_FILE_PATH = "interface/dataset_fl.csv"  # Your CSV file
IMAGE_FOLDER = "full-fundus"        # Folder containing your images

# INITIALIZATION 
utils.setup_env()

try:
    active_db_type = db.init_db()
except Exception as e:
    st.error(f"Critical Database Error: {e}")
    st.stop()

# LOAD REAL DATASET
# This replaces the mock data. It runs once per session.
if 'dataset' not in st.session_state:
    st.session_state.dataset = utils.load_dataset(CSV_FILE_PATH, IMAGE_FOLDER)

# Helper to access the dataset safely
DATASET = st.session_state.dataset

if not DATASET:
    st.error("Please ensure 'dataset.csv' exists and 'images' folder is populated.")
    st.stop() # Stop execution if no data

# SIDEBAR: SETTINGS & HISTORY 
with st.sidebar:
    st.title("⚙️ Settings")
    
    # Model Selector
    model_options = ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large", "turbo"]
    selected_model = st.selectbox("Whisper Model Size", model_options, index=1)
    
    st.divider()
    
    # History Section
    st.header(f"🗄️ History ({active_db_type})")
    
    search_input = st.text_input("🔍 Search ID", value=st.session_state.get('history_search', ""))
    if search_input != st.session_state.get('history_search', ""):
        st.session_state.history_search = search_input
        st.session_state.history_page = 1
        st.rerun()

    if 'history_page' not in st.session_state:
        st.session_state.history_page = 1
        
    ITEMS_PER_PAGE = 5
    try:
        history_data, total_items = db.get_history_paginated(
            st.session_state.get('history_search', ""), 
            st.session_state.history_page, 
            ITEMS_PER_PAGE
        )
    except Exception as e:
        st.error(f"Error fetching history: {e}")
        history_data, total_items = [], 0
    
    if not history_data:
        st.info("No diagnoses found.")
    else:
        for item in history_data:
            ts = str(item.get('createdAt'))[:16]
            img_id = item.get('imageId', 'N/A')
            text = item.get('diagnosisText', '')
            preview = (text[:50] + '..') if len(text) > 50 else text
            
            with st.expander(f"{img_id} ({ts})"):
                st.caption(ts)
                st.write(f"_{preview}_")
                
                if st.button("Load Report", key=f"load_{item.get('createdAt')}_{img_id}"):
                     # 1. Update the text
                     st.session_state.current_transcription = text
                     
                     # 2. Find and update the image index
                     found_index = -1
                     for idx, data_item in enumerate(DATASET):
                         if str(data_item['id']) == str(img_id):
                             found_index = idx
                             break
                     
                     if found_index != -1:
                         st.session_state.img_index = found_index
                     else:
                         st.warning(f"Image ID {img_id} not found in current dataset.")
                     
                     st.rerun()

    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    if total_pages > 1:
        st.divider()
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.session_state.history_page > 1:
                if st.button("◀️"):
                    st.session_state.history_page -= 1
                    st.rerun()
        with c2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px;'>{st.session_state.history_page} / {total_pages}</div>", unsafe_allow_html=True)
        with c3:
            if st.session_state.history_page < total_pages:
                if st.button("▶️"):
                    st.session_state.history_page += 1
                    st.rerun()

# LOAD MODEL 
with st.spinner(f"Loading Whisper '{selected_model}' model..."):
    model = utils.load_whisper_model(selected_model)

# SESSION STATE MANAGEMENT 
if 'img_index' not in st.session_state:
    # Default to 0
    start_index = 0
    
    # Try to find the last worked-on image from the DB
    try:
        last_id = db.get_last_active_image_id()
        if last_id:
            # Find the index of this ID in the current DATASET
            for i, item in enumerate(DATASET):
                if str(item["id"]) == str(last_id):
                    start_index = i
                    break
    except Exception as e:
        print(f"Could not restore session: {e}")
        
    st.session_state.img_index = start_index

def load_current_image_data():
    """Updates session state with DB data for the new image."""
    current_img_id = DATASET[st.session_state.img_index]["id"]
    try:
        existing_text = db.get_latest_diagnosis(current_img_id)
        st.session_state.current_transcription = existing_text if existing_text else ""
    except Exception as e:
        st.error(f"Failed to load diagnosis: {e}")
        st.session_state.current_transcription = ""
    st.session_state.last_processed_audio = None

if 'current_transcription' not in st.session_state:
    load_current_image_data()
if 'last_processed_audio' not in st.session_state:
    st.session_state.last_processed_audio = None

# MAIN CONTENT 
st.title("👁️ OphthalmoCapture")
st.caption(f"Medical Dictation System • Model: {selected_model}")

col_img, col_diag = st.columns([1.5, 1])
current_img = DATASET[st.session_state.img_index]

with col_img:
    st.image(current_img["url"], width="stretch")
    
    # Navigation
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("⬅️ Previous"):
            st.session_state.img_index = (st.session_state.img_index - 1) % len(DATASET)
            load_current_image_data()
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align: center'><b>{current_img['label']}</b><br>(ID: {current_img['id']})</div>", unsafe_allow_html=True)
    with c3:
        if st.button("Next ➡️"):
            st.session_state.img_index = (st.session_state.img_index + 1) % len(DATASET)
            load_current_image_data()
            st.rerun()

with col_diag:
    st.subheader("Dictation & Report")
    
    audio_wav = st.audio_input("Record Voice", key=f"audio_{current_img['id']}")

    if audio_wav is not None:
        if st.session_state.last_processed_audio != audio_wav:
            with st.spinner("Analyzing audio..."):
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        tmp_file.write(audio_wav.read())
                        tmp_path = tmp_file.name
                    
                    result = model.transcribe(tmp_path, language="es")
                    new_text = result["text"].strip()
                    
                    if st.session_state.current_transcription:
                        st.session_state.current_transcription += " " + new_text
                    else:
                        st.session_state.current_transcription = new_text
                    
                    st.session_state.last_processed_audio = audio_wav
                    os.remove(tmp_path)
                except Exception as e:
                    st.error(f"Transcription Error: {e}")

    diagnosis_text = st.text_area(
        "Findings:", 
        value=st.session_state.current_transcription,
        height=300
    )
    
    if diagnosis_text != st.session_state.current_transcription:
        st.session_state.current_transcription = diagnosis_text

    if st.button("💾 Save to Record", type="primary"):
        if diagnosis_text.strip():
            try:
                db.save_diagnosis(current_img['id'], diagnosis_text)
                st.success("Successfully saved to database.")
            except Exception as e:
                st.error(f"Save failed: {e}")
        else:
            st.warning("Cannot save empty diagnosis.")