import streamlit as st

from rag.config import settings
from rag.db import document_stats, health as db_health, initialize_schema
from rag.ollama_client import health as ollama_health
from rag.pdf_ingest import discover_pdfs, ingest_all
from rag.service import answer_question


st.set_page_config(
    page_title="Archivo RAG",
    page_icon=":material/library_books:",
    layout="wide",
)

schema_error = None
try:
    initialize_schema()
except Exception as exc:
    schema_error = str(exc)

db_ok, db_message = db_health() if not schema_error else (False, schema_error)
ollama_ok, ollama_message = ollama_health()
pdfs = discover_pdfs()

with st.sidebar:
    st.header("Estado del sistema")
    if db_ok:
        st.badge("PostgreSQL + pgvector", icon=":material/check:", color="green")
    else:
        st.badge("Base de datos no disponible", icon=":material/error:", color="red")
    st.caption(db_message)

    if ollama_ok:
        st.badge("Modelos locales", icon=":material/check:", color="green")
    else:
        st.badge("Ollama no disponible", icon=":material/error:", color="red")
    st.caption(ollama_message)

    st.space("small")
    st.subheader("Configuración")
    st.caption(f"Embeddings: `{settings.embedding_model}`")
    st.caption(f"Generación: `{settings.generation_model}`")
    st.caption(f"PDF detectados: {len(pdfs)}")

    ingest_disabled = not (db_ok and ollama_ok and pdfs)
    if st.button(
        "Procesar los tres PDF",
        type="primary",
        width="stretch",
        icon=":material/database_upload:",
        disabled=ingest_disabled,
    ):
        progress_bar = st.progress(0, text="Iniciando ingesta")

        def update_progress(value, message):
            progress_bar.progress(min(max(value, 0.0), 1.0), text=message)

        try:
            st.session_state["ingestion_results"] = ingest_all(update_progress)
            st.toast("Índice persistente actualizado", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"La ingesta no pudo completarse: {exc}", icon=":material/error:")

st.title("Consulta tus documentos con evidencia")
st.write(
    "Pregunta en español y recibe una respuesta sustentada en pasajes concretos. "
    "Cada fuente conserva el documento y la página física del PDF."
)
st.caption(
    f"Se procesan como máximo {settings.max_pages_per_pdf} páginas por archivo. "
    "La aplicación informa las páginas omitidas, sin texto y con errores de lectura."
)

stats = document_stats() if db_ok else []
if stats:
    total_pages = sum(item["processed_pages"] for item in stats)
    total_chunks = sum(item["chunk_count"] for item in stats)
    cols = st.columns(3)
    cols[0].metric("Documentos indexados", len(stats), border=True)
    cols[1].metric("Páginas procesadas", total_pages, border=True)
    cols[2].metric("Fragmentos persistidos", total_chunks, border=True)

    with st.expander("Detalle de la ingesta", icon=":material/description:"):
        for item in stats:
            st.markdown(f"**{item['name']}**")
            st.caption(
                f"{item['processed_pages']} de {item['page_count']} páginas · "
                f"{item['omitted_pages']} omitidas · {item['chunk_count']} fragmentos"
            )
            if item["pages_without_text"]:
                st.warning(
                    "Páginas sin texto: " + ", ".join(map(str, item["pages_without_text"])),
                    icon=":material/warning:",
                )
            if item["read_errors"]:
                st.error(
                    f"Errores de lectura: {len(item['read_errors'])}",
                    icon=":material/error:",
                )
else:
    st.info(
        "Aún no existe un índice. Usa “Procesar los tres PDF” en la barra lateral.",
        icon=":material/info:",
    )

if st.session_state.get("ingestion_results"):
    with st.expander("Resultado de la última ejecución", expanded=True, icon=":material/task_alt:"):
        for result in st.session_state["ingestion_results"]:
            label = "Sin cambios" if result.status == "sin cambios" else "Procesado"
            color = "blue" if result.status == "sin cambios" else "green"
            st.badge(label, color=color)
            st.markdown(f"**{result.name}**")
            st.caption(
                f"{result.processed_pages}/{result.page_count} páginas · "
                f"{result.chunk_count} fragmentos · {result.omitted_pages} omitidas"
            )

document_names = [item["name"] for item in stats]
with st.form("question_form"):
    selected = st.selectbox("Buscar en", ["Todos los documentos", *document_names])
    question = st.text_area(
        "Pregunta en español",
        placeholder="Ejemplo: ¿Qué responsabilidades tiene una vista en una aplicación Django?",
        height=110,
    )
    top_k = st.slider("Pasajes para recuperar", min_value=3, max_value=8, value=5)
    submitted = st.form_submit_button(
        "Responder con evidencia",
        type="primary",
        width="stretch",
        icon=":material/search:",
        disabled=not (stats and ollama_ok),
    )

if submitted:
    if not question.strip():
        st.warning("Escribe una pregunta antes de continuar.", icon=":material/warning:")
    else:
        document_filter = None if selected == "Todos los documentos" else selected
        with st.spinner("Recuperando pasajes y generando la respuesta..."):
            try:
                answer, passages = answer_question(question.strip(), document_filter, top_k)
                st.session_state["last_answer"] = answer
                st.session_state["last_passages"] = passages
            except Exception as exc:
                st.error(f"No fue posible responder: {exc}", icon=":material/error:")

if st.session_state.get("last_answer"):
    st.subheader("Respuesta")
    with st.container(border=True):
        st.markdown(st.session_state["last_answer"])
    st.subheader("Pasajes utilizados")
    for index, passage in enumerate(st.session_state.get("last_passages", []), start=1):
        title = f"{index}. {passage['document']} · página {passage['page']}"
        with st.expander(title, icon=":material/article:"):
            st.caption(f"Similitud semántica: {passage['score']:.3f}")
            st.write(passage["content"])
