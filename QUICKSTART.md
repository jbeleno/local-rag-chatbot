# Guía de Inicio Rápido

## Pasos Rápidos para Empezar

### 1. Crear archivo .env

Crea un archivo `.env` en la raíz del proyecto con este contenido:

```env
CHUNK_SIZE=700
CHUNK_OVERLAP=100
TOP_K_RESULTS=4
LLM_MODEL=llama3.1
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./data/chroma_db
DOCUMENTS_DIR=./data/documents
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.1
```

### 2. Instalar Ollama y descargar modelo

```bash
# Descargar Ollama desde https://ollama.ai
# Luego descargar un modelo:
ollama pull llama3.1
```

### 3. Instalar dependencias Python

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Activar (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Iniciar servidor

```bash
uvicorn app.main:app --reload
```

### 5. Probar el sistema

1. Abre http://localhost:8000/docs
2. Sube un documento PDF/TXT/DOCX usando `/api/documents/upload`
3. Haz una pregunta usando `/api/chat/query`

## Solución de Problemas Comunes

### Error: "Connection refused" con Ollama
- Verifica que Ollama esté corriendo: `ollama list`
- Verifica que la URL en `.env` sea correcta

### Error: "Model not found"
- Descarga el modelo: `ollama pull llama3.1`
- Verifica el nombre en `.env`

### Error al instalar dependencias
- Actualiza pip: `pip install --upgrade pip`
- Instala dependencias una por una si hay conflictos

### Memoria insuficiente
- Usa modelos más pequeños (llama3.1:8b)
- Reduce CHUNK_SIZE en `.env`

