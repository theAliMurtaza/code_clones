---
title: CloneScope Model
emoji: 🔎
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.9.0
python_version: "3.10"
app_file: app.py
pinned: false
models:
  - microsoft/graphcodebert-base
---

# CloneScope model service

Select **ZeroGPU** hardware in Space Settings and set `SEMANTIC_API_KEY` as a
Secret before starting the app. Gradio API names: `/info`, `/embed`, `/predict`.
Requests require the `X-Semantic-Api-Key` header. Render uses a Hugging Face token
separately for Space access and ZeroGPU quota attribution.

This deployment performs inference. It does not train the model or prove program
equivalence. The failed Java training pilot is intentionally not bundled.
No database or frontend configuration belongs in this model-only Space.
