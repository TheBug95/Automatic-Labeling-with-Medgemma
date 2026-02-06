import streamlit as st
import whisper
import os
import pandas as pd


@st.cache_resource
def load_whisper_model(model_size):
    """Loads the Whisper model (Cached)."""
    print(f"Loading Whisper model: {model_size}...")
    return whisper.load_model(model_size)

def setup_env():
    """Sets up environment variables."""
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def load_dataset(csv_path, image_folder):
    """
    Reads a CSV and checks for image existence.
    Expected CSV columns: 'filename' (required), 'label' (optional).
    """
    images_list = []
    
    # 1. Check if CSV exists
    if not os.path.exists(csv_path):
        st.error(f"⚠️ CSV file not found: {csv_path}")
        return []

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return []

    # 2. Iterate through CSV
    # We look for a 'filename' column. If not found, use the first column.
    filename_col = 'filename'
    if 'filename' not in df.columns:
        filename_col = df.columns[0]
        st.warning(f"Column 'filename' not found. Using '{filename_col}' as filename.")

    for index, row in df.iterrows():
        base_name = str(row[filename_col]).strip()
        
        # Construct full path
        full_path = os.path.join(image_folder, base_name)
        
        # Handle extensions if filename doesn't have them (optional check)
        if not os.path.exists(full_path):
            # Try adding common extensions if file not found
            for ext in ['.jpg', '.png', '.jpeg', '.tif']:
                if os.path.exists(full_path + ext):
                    full_path = full_path + ext
                    break
        
        # Only add if file actually exists
        if os.path.exists(full_path):
            images_list.append({
                "id": base_name,
                "label": row.get('label', base_name), # Use 'label' column or fallback to name
                "url": full_path # Streamlit accepts local paths here
            })
    
    if not images_list:
        st.warning(f"No valid images found in '{image_folder}' matching the CSV.")
        
    return images_list