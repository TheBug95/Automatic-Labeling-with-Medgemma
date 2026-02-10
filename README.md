---
title: OphthalmoCapture
emoji: 👁️
colorFrom: blue
colorTo: green
sdk: docker
app_file: interface/main.py
pinned: false
---

# 👁️ OphthalmoCapture

**Sistema de Etiquetado Médico Oftalmológico** — Interfaz web para cargar imágenes de fondo de ojo, etiquetarlas (catarata / no catarata), dictar observaciones por voz con transcripción automática (Whisper) y descargar el paquete de etiquetado completo.

> **Modelo de sesión efímera:** las imágenes y el audio viven únicamente en la memoria del navegador/servidor durante la sesión. Nunca se persisten en disco ni en base de datos. Solo se almacenan metadatos de auditoría (etiqueta, transcripción, médico, fecha).

---

## 1. Requisitos previos

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| **Python** | 3.10+ | Recomendado 3.11 |
| **pip** | 23+ | — |
| **FFmpeg** | cualquier versión reciente | Necesario para OpenAI Whisper. [Instrucciones de instalación](https://ffmpeg.org/download.html) |
| **GPU (opcional)** | CUDA 11.8+ | Acelera la transcripción con Whisper. Funciona sin GPU usando CPU. |

---

## 2. Instalación

### A. Clonar el repositorio

```bash
git clone <URL_DEL_REPO>
cd Automatic-Labeling-with-Medgemma
```

### B. Crear un entorno virtual (recomendado)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### C. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instala: `streamlit`, `openai-whisper`, `torch`, `pandas`, `pillow`, `streamlit-authenticator` y demás dependencias.

> **Nota sobre PyTorch:** si tienes GPU NVIDIA y quieres usarla para Whisper, instala la versión con CUDA antes de instalar los requisitos:
> ```bash
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
> pip install -r requirements.txt
> ```

### D. Verificar FFmpeg

```bash
ffmpeg -version
```

Si no está instalado:
- **Windows:** `winget install ffmpeg` o descargar desde [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

---

## 3. Ejecutar la interfaz web (Streamlit)

```bash
streamlit run interface/main.py
```

Se abrirá automáticamente en el navegador en **http://localhost:8501**.

### Flujo de uso

1. **Autenticación** — Si `streamlit-authenticator` está instalado, inicia sesión con las credenciales configuradas. Si no, entra en modo anónimo automáticamente.
2. **Cargar imágenes** — Arrastra o selecciona imágenes de fondo de ojo (JPG, PNG, TIFF, máx. 50 MB cada una).
3. **Galería** — Se muestra una tira de miniaturas con indicadores 🔴 (pendiente) / 🟢 (etiquetada). Haz clic para seleccionar.
4. **Etiquetar** — Clasifica la imagen como *Catarata* o *No Catarata*.
5. **Dictar observaciones** — Graba audio con el micrófono. Whisper transcribe automáticamente con timestamps. Puedes editar el texto resultante.
6. **Descargar** — Descarga un ZIP individual (imagen + metadatos + audio + transcripción) o un paquete de la sesión completa. También disponible en formatos ML (HuggingFace CSV, JSONL).
7. **Finalizar sesión** — El botón del sidebar limpia toda la memoria. También hay timeout automático de 30 min de inactividad.

### Configuración

Los parámetros se encuentran en `interface/config.py`:

| Parámetro | Valor por defecto | Descripción |
|-----------|-------------------|-------------|
| `SESSION_TIMEOUT_MINUTES` | 30 | Minutos de inactividad antes de limpiar la sesión |
| `MAX_UPLOAD_SIZE_MB` | 50 | Tamaño máximo por imagen |
| `ALLOWED_EXTENSIONS` | jpg, jpeg, png, tif | Formatos de imagen aceptados |
| `WHISPER_MODEL_OPTIONS` | tiny → turbo | Modelos de Whisper disponibles |
| `DEFAULT_WHISPER_LANGUAGE` | es | Idioma por defecto para transcripción |
| `UI_LANGUAGE` | es | Idioma de la interfaz (es / en) |
| `LABEL_OPTIONS` | Catarata, No Catarata | Categorías de etiquetado |

### Credenciales por defecto (modo autenticación)

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | admin123 | Administrador |
| doctor1 | admin123 | Médico |
| doctor2 | admin123 | Médico |

> ⚠️ Cambia estas credenciales en `interface/services/auth_service.py` antes de cualquier uso en producción.

---

## 4. Estructura del proyecto

```
interface/
├── main.py                  # Orquestador principal de Streamlit
├── config.py                # Constantes de configuración
├── database.py              # Persistencia de metadatos (SQLite)
├── utils.py                 # Utilidades generales (validación de imágenes)
├── i18n.py                  # Internacionalización (es/en)
├── components/
│   ├── uploader.py          # Carga de imágenes con validación
│   ├── gallery.py           # Galería de miniaturas con estado
│   ├── labeler.py           # Clasificación (catarata / no catarata)
│   ├── recorder.py          # Grabación de audio + transcripción Whisper
│   └── downloader.py        # Descarga individual, masiva y formatos ML
├── services/
│   ├── session_manager.py   # Gestión de sesión efímera en memoria
│   ├── whisper_service.py   # Carga y transcripción con Whisper
│   ├── export_service.py    # Generación de ZIP, CSV, JSONL
│   └── auth_service.py      # Autenticación (opcional)
└── .streamlit/
    └── config.toml          # Configuración de Streamlit
```

---

## 5. Ejecutar el Notebook (Jupyter)

Para explorar el modelo MedGemma, afinar parámetros o depurar:

```bash
jupyter notebook medgemma.ipynb
```

Ejecuta las celdas secuencialmente con **Shift + Enter**.

---

## 6. Solución de problemas

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'whisper'` | `pip install openai-whisper` |
| `FileNotFoundError: ffmpeg not found` | Instala FFmpeg (ver sección 2.D) |
| Audio no se graba en el navegador | Asegúrate de acceder por `localhost` o HTTPS. Los navegadores bloquean el micrófono en HTTP no local. |
| `streamlit-authenticator` no disponible | La app funciona en modo anónimo automáticamente. Instalar con `pip install streamlit-authenticator` si se desea autenticación. |
| Timeout de sesión inesperado | Ajusta `SESSION_TIMEOUT_MINUTES` en `config.py` |
| Imágenes no se cargan | Verifica que el formato sea JPG/PNG/TIFF y que no supere 50 MB |
