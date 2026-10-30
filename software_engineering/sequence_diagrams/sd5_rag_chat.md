# SD-5. RAG chat request (planned P2, adapter from P3)

[← Sequence diagrams](README.md) · [Hub](../README.md) · Previous: [SD-4](sd4_feature_pipeline.md) · Next: [SD-6](sd6_datasets_training_eval.md)

| | |
|---|---|
| Status | Planned P2 (P3 adapter) |
| Requirements | [INF](../requirements/requirements.md#214-rag-inference-service-inf) 001, 002, 003, 004, 005, 006, 007, 008 · [OPS](../requirements/requirements.md#215-llmops-monitoring-cicd-deployment-ops) 001, 008 · [REG](../requirements/requirements.md#22-source-registry-and-multi-user-reg) 010 |
| User stories | US-014, US-067, US-068, US-069, US-070, US-071, US-072, US-087, US-088 ([backlog](../user_stories/user_stories.md)) |
| Use cases | [UC-16](../use_cases/04_rag_chat_and_features.md#uc-16-chat-with-the-twin), [UC-17](../use_cases/04_rag_chat_and_features.md#uc-17-give-feedback-on-an-answer) |
| Class diagrams | [7](../class_diagrams/07_feature_pipeline.md), [9](../class_diagrams/09_llm_clients_inference_and_llmops.md), [10a](../class_diagrams/10a_ui_api_and_authentication.md) |
| draw.io | copy the ```mermaid block below → Arrange › Insert › Advanced › Mermaid |


INF-001..008, OPS-001, OPS-008, REG-010, NFR-SEC-006. `OwnerScope` is the only place the user filter is built; the answer cites only retrieved chunks.

```mermaid
sequenceDiagram
  autonumber
  actor Consumer as Twin consumer
  participant Api as ApiApp
  participant Auth as AuthService
  participant Rate as RateLimiter
  participant Twin as TwinService
  participant Tracer as Tracer
  participant Ret as Retriever
  participant QE as QueryExpander
  participant SQ as SelfQueryExtractor
  participant Emb as Embedder
  participant VS as VectorStore
  participant Rr as CrossEncoderReranker
  participant Prompts as PromptRegistry
  participant Res as ModelResolver
  participant Budget as BudgetGuard
  participant LLM as LLMClient

  Consumer->>Api: POST /api/v1/twins/{user_id}/chat (query, history)
  Api->>Auth: authenticate(token)
  Auth-->>Api: Principal (P2 static bearer token, P4 per-user session)
  Api->>Api: principal.require_self(user_id) (403 otherwise, P4)
  Api->>Rate: allow(user, limit, window)
  alt over the rate limit
    Api-->>Consumer: 429
  else
    Api->>Twin: answer(ChatRequest)
    Twin->>Tracer: start(chat, user_id): trace_id
    Twin->>Ret: retrieve(query, user_id)
    Ret->>QE: expand(query)
    Ret->>SQ: extract(query): topic and kind filters
    Ret->>Ret: VectorFilter.for_user(user_id) via OwnerScope (own + shared external, not deleted)
    Ret->>Emb: embed(expanded queries)
    Ret->>VS: search(vector, filter, k)
    Ret->>Rr: rerank(query, chunks, k)
    Ret-->>Twin: top-k ScoredChunks
    alt every score below the relevance threshold
      Twin-->>Api: "I don't know" answer, no citations (INF-007)
    else
      Twin->>Prompts: get(twin_answer): PromptTemplate (versioned)
      Twin->>Twin: render(query, history, chunks as untrusted context)
      Twin->>Res: client_for(user_id)
      Res-->>Twin: AdapterModelClient (production tag) or BaseModelClient fallback
      Twin->>LLM: estimate_cost_usd(prompt, max_tokens)
      Twin->>Budget: ensure(inference, estimate, user_id)
      alt daily cap reached
        Budget-->>Api: 503 budget_exhausted
      else
        Twin->>LLM: generate(prompt) or stream(prompt)
        LLM-->>Twin: Completion (text, tokens)
        Twin->>Budget: charge(CostEntry with user_id, trace_id)
        Twin->>Twin: keep only citations of retrieved chunks
        Twin->>Tracer: record(Trace: prompt version, chunk ids, model version, latency, tokens, cost)
        Twin-->>Api: ChatResponse(answer, sources, model_version, trace_id, ai_disclosure)
      end
    end
    Api-->>Consumer: 200 answer + citations + AI disclosure
  end
  opt feedback (P4)
    Consumer->>Api: thumbs up/down on trace_id
    Api->>Tracer: record_feedback(Feedback)
  end
```
