# Frontend - Chatbot RAG Local

Interfaz web para interactuar con el chatbot RAG.

## Estructura

- `index.html` - Interfaz principal del chatbot

## Uso

Simplemente abre `index.html` en tu navegador o sirve los archivos con un servidor HTTP simple:

```bash
# Con Python
python -m http.server 3000

# Con Node.js (http-server)
npx http-server -p 3000
```

Luego abre `http://localhost:3000` en tu navegador.

## Configuración

Asegúrate de que el backend esté corriendo en `http://localhost:8000` o actualiza `API_BASE_URL` en `index.html`.

