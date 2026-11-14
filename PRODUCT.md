# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated by the user: Python, Streamlit, PostgreSQL with pgvector, Docker and local Ollama models. The choices prioritize a simple setup without paid APIs.

## Users

The primary user is a student demonstrating a laboratory assignment. The user asks questions in Spanish about three supplied technical PDF documents and needs evidence tied to the physical PDF page.

## Product Purpose

Ingest the three supplied PDFs, persist their fragments and embeddings in PostgreSQL, retrieve relevant passages semantically and answer Spanish questions with document and page citations.

## Operating Context

The application runs locally for a graded demonstration. It reads the three PDFs from `D:\UTEC\ICC\LAB_6\SEGUNDO`, processes at most 300 pages from each file and preserves the vector index after restarts.

## Capabilities and Constraints

- Three PDFs are queried together or individually.
- Each fragment records document name and physical PDF page starting at 1.
- PostgreSQL with pgvector persists documents, fragments and embeddings.
- Reprocessing the same files is idempotent.
- Pages without selectable text and reading errors are reported.
- Answers are generated in Spanish with a citation for each relevant claim.
- Retrieved passages are visible below the answer.
- Insufficient evidence is stated explicitly.
- The current source files exceed the assignment limit, so only the first 300 pages of each are ingested and the omitted count is reported.

## Evidence on Hand

- Three supplied PDF files in `D:\UTEC\ICC\LAB_6\SEGUNDO`.
- Page counts: 717, 837 and 827.
- No paid model API key was supplied; local Ollama models are used.

## Product Principles

- Make every answer auditable from document and page.
- Show system state and ingestion limits plainly.
- Keep setup and demonstration steps short.
- Persist work so restarts do not require reprocessing.
