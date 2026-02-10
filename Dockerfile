# ── OphthalmoCapture – Hugging Face Spaces (Docker + Streamlit) ──────────────
FROM python:3.10-slim

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (HF Spaces requirement) ───────────────────────────────────
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# ── Python dependencies ──────────────────────────────────────────────────────
COPY --chown=user requirements.txt .
USER user
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Pre-download Whisper model (base.en) to bake into image ─────────────────
# This avoids a ~150 MB download on every cold start.
# Change to "small" / "medium" if you upgrade hardware.
RUN python -c "import whisper; whisper.load_model('base.en')"

# ── Copy application code ───────────────────────────────────────────────────
COPY --chown=user . .

# ── Streamlit configuration ─────────────────────────────────────────────────
# HF Spaces expects port 7860
EXPOSE 7860

HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health || exit 1

# ── Launch ───────────────────────────────────────────────────────────────────
ENTRYPOINT ["streamlit", "run", "interface/main.py", \
            "--server.port=7860", \
            "--server.address=0.0.0.0", \
            "--server.enableCORS=false", \
            "--server.enableXsrfProtection=false", \
            "--browser.gatherUsageStats=false"]
