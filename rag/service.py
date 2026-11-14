from .db import retrieve
from .ollama_client import embed, generate, translate_query


MINIMUM_RELEVANCE = 0.22


def answer_question(question: str, document_name: str | None, top_k: int) -> tuple[str, list[dict]]:
    semantic_query = translate_query(question)
    question_embedding = embed([semantic_query])[0]
    passages = retrieve(question_embedding, document_name, top_k)
    if not passages or passages[0]["score"] < MINIMUM_RELEVANCE:
        return "No hay evidencia suficiente en los documentos recuperados.", passages
    return generate(question, passages), passages
