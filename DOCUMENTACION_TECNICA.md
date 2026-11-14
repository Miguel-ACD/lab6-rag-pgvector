# Documentación técnica

## Repositorio de la actividad 2

Código, instrucciones y evidencias: https://github.com/Miguel-ACD/lab6-rag-pgvector

## Objetivo

La aplicación implementa un flujo RAG local para consultar en español tres libros PDF. La solución procesa hasta 300 páginas físicas por documento, recupera pasajes mediante similitud semántica y genera respuestas breves con evidencia verificable.

## Componentes

- **Streamlit:** interfaz web y selección de todos los documentos o un PDF específico.
- **pypdf:** extracción del texto y numeración física desde 1.
- **Ollama + nomic-embed-text:** embeddings locales de 768 dimensiones.
- **Ollama + llama3.2:3b:** traducción semántica de la consulta y respuesta en español.
- **PostgreSQL 17 + pgvector:** almacenamiento persistente y búsqueda vectorial.
- **Docker Compose:** ejecución reproducible de la aplicación y la base de datos.

## Flujo de ingesta

1. Se detectan los tres archivos montados en `/pdfs` en modo de solo lectura.
2. Se calcula SHA-256 para identificar si cada archivo cambió.
3. Se leen como máximo las primeras 300 páginas físicas.
4. Se reportan páginas omitidas, páginas sin texto y errores de lectura.
5. El texto se divide en fragmentos con solapamiento y se generan embeddings por lotes.
6. Documentos, páginas, fragmentos y vectores se guardan en PostgreSQL.

Si el nombre y SHA-256 coinciden con una ejecución anterior, el archivo queda con estado `sin cambios` y no se duplican registros.

## Modelo de datos

`documents` almacena nombre, hash, páginas totales y procesadas, páginas omitidas, páginas sin texto, errores y conteo de fragmentos. `chunks` almacena documento, página física, índice, contenido y `vector(768)`. Un índice HNSW con distancia coseno permite la recuperación semántica.

## Consulta RAG

La pregunta española se convierte en una consulta semántica inglesa para alinearla con los libros. PostgreSQL/pgvector recupera los pasajes más cercanos, opcionalmente filtrados por documento. La respuesta utiliza el pasaje principal y la aplicación añade una cita exacta `[Documento, p. N]` a cada afirmación. Debajo se muestran los pasajes y sus puntuaciones.

Si no existe un pasaje con relevancia mínima, se devuelve: `No hay evidencia suficiente en los documentos recuperados.`

## Verificación realizada

- Ingesta: 3 documentos, 900 páginas y 1,239 fragmentos.
- Persistencia: después de reiniciar los contenedores se conservaron los mismos conteos.
- Idempotencia: la segunda ejecución informó `sin cambios` para los tres PDF.
- Recuperación: consulta filtrada al libro de Django con cita y pasajes visibles.
- Pruebas automatizadas: 2 pruebas aprobadas.

## Seguridad y alcance

Los PDF se montan en modo de solo lectura, las credenciales locales están en `.env` excluido de Git y los modelos trabajan localmente. La aplicación no sube los libros al repositorio ni a servicios externos.
