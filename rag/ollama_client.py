from collections.abc import Iterable
import re

import requests

from .config import settings


class OllamaError(RuntimeError):
    pass


def health() -> tuple[bool, str]:
    try:
        response = requests.get(f"{settings.ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        names = {model["name"].split(":")[0] for model in response.json().get("models", [])}
        required = {settings.embedding_model.split(":")[0], settings.generation_model.split(":")[0]}
        missing = sorted(required - names)
        if missing:
            return False, "Faltan modelos: " + ", ".join(missing)
        return True, "Modelos locales disponibles"
    except Exception as exc:
        return False, str(exc)


def embed(texts: Iterable[str]) -> list[list[float]]:
    values = list(texts)
    response = requests.post(
        f"{settings.ollama_url}/api/embed",
        json={"model": settings.embedding_model, "input": values},
        timeout=300,
    )
    if not response.ok:
        raise OllamaError(f"Error de embeddings: {response.text[:300]}")
    embeddings = response.json().get("embeddings", [])
    if len(embeddings) != len(values):
        raise OllamaError("Ollama devolvió una cantidad inesperada de embeddings")
    if embeddings and len(embeddings[0]) != settings.embedding_dim:
        raise OllamaError(
            f"Dimensión recibida {len(embeddings[0])}; se esperaba {settings.embedding_dim}"
        )
    return embeddings


def translate_query(question: str) -> str:
    response = requests.post(
        f"{settings.ollama_url}/api/generate",
        json={
            "model": settings.generation_model,
            "prompt": (
                "Translate the following Spanish search question into concise English. "
                "Return only the translation, without explanations:\n" + question
            ),
            "stream": False,
            "options": {"temperature": 0, "num_predict": 120},
        },
        timeout=180,
    )
    if not response.ok:
        raise OllamaError(f"Error al traducir la consulta: {response.text[:300]}")
    translated = response.json().get("response", "").strip()
    return translated or question


def generate(question: str, passages: list[dict]) -> str:
    primary = passages[0]
    context = "\n\n".join(
        f"[FUENTE {index}] Documento: {item['document']} | Página física: {item['page']}\n{item['content']}"
        for index, item in enumerate(passages[:1], start=1)
    )
    prompt = f"""Eres un asistente de consulta documental.
Responde exclusivamente con la evidencia incluida abajo y siempre en español.
Escribe únicamente de 2 a 3 viñetas breves con afirmaciones factuales.
No agregues introducción, conclusión, citas ni bibliografía; la aplicación añadirá las citas.
No inventes datos ni cites páginas que no aparecen en las fuentes.
Si la evidencia no permite responder, responde exactamente: No hay evidencia suficiente en los documentos recuperados.
Después de la respuesta no agregues una bibliografía separada.

PREGUNTA:
{question}

FUENTES RECUPERADAS:
{context}
"""
    response = requests.post(
        f"{settings.ollama_url}/api/generate",
        json={
            "model": settings.generation_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 450},
        },
        timeout=300,
    )
    if not response.ok:
        raise OllamaError(f"Error de generación: {response.text[:300]}")
    answer = response.json().get("response", "").strip()
    if answer == "No hay evidencia suficiente en los documentos recuperados.":
        return answer

    citation = f"[{primary['document']}, p. {primary['page']}]"
    cited_lines = []
    for line in (item.strip() for item in answer.splitlines()):
        if not line:
            continue
        claim = re.sub(r"\[[^\]]+\]", "", line.lstrip("-*• ")).strip()
        if claim and not claim.casefold().startswith(("aquí", "respuesta")):
            cited_lines.append(f"- {claim} {citation}")
        if len(cited_lines) == 3:
            break
    return "\n".join(cited_lines) or f"- {answer} {citation}"
