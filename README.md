# CloneScope - LLM-Powered Code Clone Detection
## React 18 + Vite + Tailwind CSS v3

## Quick Start

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build
```

## Clone Types Shown
- Type-1 (Green)  - Exact copy, whitespace/comment differences only
- Type-2 (Cyan)   - Same structure, identifiers renamed
- Type-3 (Amber)  - Near-miss, statements added/removed
- Type-4 (Violet) - Semantic clone, different implementation

Each pair shows: side-by-side code viewer, highlighted clone lines with line numbers, similarity score, cross-language badge.

## Pages
- Dashboard     - Stats, 2 projects (Python/Java), clone type guide
- Code Ingestion - FR-01: upload, Git URL, paste code
- Tokenizer      - FR-02/FR-03: pipeline config + CodeBERT embedding
- Clone Detection - FR-04/05/06: Type 1-4 pairs with code viewer
- Results        - FR-09: metrics, export, annotated clone viewer
- Benchmarking   - FR-10: BigCloneBench, baselines, NFR status
- My Projects    - FR-08: auth, session history

## Stack: React 18, Vite 5, Tailwind CSS v3, Recharts, Inter + JetBrains Mono
