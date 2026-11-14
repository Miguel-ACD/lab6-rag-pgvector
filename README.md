# Laboratorio 6 RAG con PostgreSQL y pgvector

Aplicación de la pregunta 2 del Laboratorio 6. Permite realizar preguntas en español sobre tres PDF y responde con citas de documento, página física y pasajes recuperados.

**Estudiante:** Miguel Angel Champi Hinojosa  
**Código:** 202110072  
**Curso:** Introducción a Cognitive Computing  
**Docente:** Farfán Madariaga, Jaime Moshe

## Funciones

- Ingesta de tres PDF con identificación por documento y página física.
- Límite configurable de 300 páginas por archivo.
- Reporte de páginas sin texto, páginas omitidas y errores de lectura.
- Persistencia de documentos, fragmentos y embeddings en PostgreSQL.
- Búsqueda semántica con pgvector.
- Consulta conjunta o filtrada por documento.
- Respuesta en español con citas y pasajes utilizados.
- Mensaje explícito cuando la evidencia es insuficiente.
- Reingesta idempotente: un PDF sin cambios no duplica documentos ni fragmentos.

## Arquitectura

- Streamlit: interfaz web.
- PostgreSQL 17 con pgvector: índice persistente.
- Ollama `nomic-embed-text`: embeddings de los documentos en inglés.
- Ollama `llama3.2:3b`: traducción semántica de la pregunta y generación en español.
- Docker Compose: aplicación y base de datos.

## Ejecución

1. Iniciar Ollama.
2. Descargar los modelos:

   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.2:3b
   ```

3. Copiar `.env.example` como `.env`.
4. Ejecutar:

   ```bash
   docker compose up --build -d
   ```

5. Abrir `http://localhost:8501`.
6. Pulsar **Procesar los tres PDF**.

La carpeta `D:\UTEC\ICC\LAB_6\SEGUNDO` se monta en modo de solo lectura dentro del contenedor.

## Límite aplicado a los archivos suministrados

Los PDF encontrados tienen 717, 837 y 827 páginas. Para respetar el límite del enunciado, se procesan las primeras 300 páginas de cada archivo: 900 páginas en total. La interfaz reporta las páginas restantes como omitidas.

## Verificación de persistencia

Después de la primera ingesta, reiniciar los contenedores con `docker compose restart`. Los documentos y fragmentos permanecen en el volumen `pgvector_data`. Al pulsar de nuevo el botón de ingesta, los archivos sin cambios aparecen con estado `sin cambios` y conservan los mismos conteos.

## Resultado verificado

- 3 documentos indexados.
- 900 páginas procesadas.
- 1,239 fragmentos con embeddings.
- Segunda ejecución: los tres archivos quedaron `sin cambios` y conservaron los mismos conteos.
- Consulta filtrada al PDF de Django con respuesta en español, cita de documento/página y pasaje recuperado.

Las capturas mínimas están en [`evidencias/`](evidencias/) y el detalle de la solución en [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md).

## Pruebas

```bash
pytest -q
```

Resultado: `2 passed`.
