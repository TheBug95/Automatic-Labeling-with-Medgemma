# How to Run MedGemma

This guide explains how to set up the environment and run both the Streamlit interface and the Jupyter Notebook for the MedGemma project.

## 1. Prerequisites & Setup

### A. Download the Dataset

The application requires the fundus image dataset to function.

1. **Download:** [**Click here to download full-fundus.zip**](https://upm365-my.sharepoint.com/:u:/g/personal/angelmario_garcia_upm_es/IQCP3cLo1x3tRK_TFCrt2HR0AfSAca5rzHrwaRa4Cm-EfL4?e=UcrIgy)
2. **Extract:** Unzip the file into the root directory of your project.
   * **Verify:** Ensure you see a folder named `full-fundus/` in your project folder.

### B. Install Dependencies

Make sure you have Python installed, then run:

```bash
pip install streamlit notebook torch transformers pillow whisper numba
````

-----

## 2. Running the Web Interface (Streamlit)

Use this method for a user-friendly dashboard to analyze images.

1. Open your terminal (Command Prompt or Terminal).
2. Navigate to your project folder:

    ```bash
    cd /path/to/your/project
    ```

3. Run the Streamlit application:

    ```bash
    streamlit run interface/main.py
    ```

4. A new tab will open in your browser automatically at `http://localhost:8501`.

-----

## 3\. Running the Notebook (Jupyter)

Use this method to see the code logic, fine-tune the model, or debug.

1. Open your terminal and navigate to the project folder.
2. Launch Jupyter:

    ```bash
    jupyter notebook medgemma.ipynb
    ```

3. The Jupyter interface will open in your browser.
4. Click on `medgemma.ipynb`.
5. Run the cells sequentially (Shift + Enter) to execute the model.
