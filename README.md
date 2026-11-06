# DocForge

DocForge is a publicly deployed, free-first, multi-user PDF RAG (Retrieval-Augmented Generation) application designed for high retrieval accuracy, grounded citations, and reliable source verification.

## Core Documentation

DocForge strictly follows an authoritative set of six core project specification documents:

- [`architecture.md`](file:///architecture.md): Technical architecture, decisions register, and system design
- [`prd.md`](file:///prd.md): Product requirements, functional scope, and success metrics
- [`design.md`](file:///design.md): User experience, UI behavior, and interface design
- [`phases.md`](file:///phases.md): Implementation phases and definition of done
- [`rules.md`](file:///rules.md): Collaborative engineering rules and implementation guidelines
- [`memory.md`](file:///memory.md): Current project state, environment details, and execution log

## Project Layout

- `backend/`: FastAPI application, domain logic, adapters, Celery tasks, and tests
- `frontend/`: React + TypeScript + Vite + Tailwind user interface
- `evaluation/`: Benchmark corpus, question labels, and RAG evaluation harness

