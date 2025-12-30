# ADR 001: Google Gemini as LLM Provider

**Status:** Accepted  
**Date:** 2025-12-29  
**Deciders:** Engineering Team  
**Context:** RAG Corp - Retrieval-Augmented Generation for Corporate Documents

---

## Context and Problem Statement

The RAG Corp system requires an LLM (Large Language Model) provider to generate natural language responses based on retrieved document chunks. We need to select a provider that balances:

- **Cost-effectiveness** for startup/MVP phase
- **Quality** of generated responses
- **Latency** for acceptable user experience
- **API simplicity** for rapid integration
- **Scalability** for future growth

## Decision Drivers

- Budget constraints during MVP development
- Need for high-quality embeddings and text generation
- Simple API integration with Python FastAPI backend
- Support for both embeddings and chat completion in one provider
- Reliable service with good uptime
- Future-proof with potential for model upgrades

## Considered Options

### Option 1: OpenAI (GPT-4/GPT-3.5)
- **Pros:**
  - Industry-leading quality
  - Mature API with extensive documentation
  - Large developer community
  - Excellent embeddings (text-embedding-3-small/large)
- **Cons:**
  - Higher cost per token (~$10/1M tokens for GPT-4-turbo)
  - Rate limits on free tier
  - Requires separate billing setup

### Option 2: Google Gemini (gemini-1.5-flash)
- **Pros:**
  - Very competitive pricing ($0.075/1M input tokens)
  - High free tier (15 RPM, 1M tokens/min)
  - Fast inference with flash model
  - Integrated embeddings (text-embedding-004)
  - Single SDK for both embeddings and generation
  - 1M context window
- **Cons:**
  - Relatively newer API (less community support)
  - Quality slightly below GPT-4 (but above GPT-3.5)

### Option 3: Anthropic Claude
- **Pros:**
  - Strong reasoning capabilities
  - Good context handling (200K tokens)
  - Constitutional AI approach
- **Cons:**
  - Higher cost than Gemini
  - Separate embeddings provider needed
  - More complex integration

### Option 4: Self-hosted (Llama 2, Mistral)
- **Pros:**
  - No per-token costs
  - Full control over data
  - No rate limits
- **Cons:**
  - Infrastructure costs (GPU hosting)
  - Maintenance overhead
  - Lower quality than commercial models
  - Operational complexity

## Decision Outcome

**Chosen option:** Google Gemini (gemini-1.5-flash + text-embedding-004)

### Rationale

1. **Cost Efficiency:**
   - Gemini Flash: $0.075/1M input tokens (13x cheaper than GPT-4-turbo)
   - Gemini Embeddings: Free tier covers MVP needs
   - Total estimated cost: ~$5-20/month during development

2. **Quality vs. Cost Balance:**
   - Flash model quality sufficient for corporate Q&A use case
   - Embeddings quality comparable to OpenAI text-embedding-3-small
   - 1M token context window enables handling large documents

3. **Developer Experience:**
   - Single SDK (`google-generativeai` Python package)
   - Unified API for embeddings and generation
   - Simple authentication via API key
   - Good documentation and examples

4. **Scalability:**
   - Free tier: 15 RPM, 1M tokens/min (sufficient for 100s of users)
   - Easy upgrade path to paid tier when needed
   - Google Cloud infrastructure reliability

### Implementation

```python
# services/rag-api/app/llm.py
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
```

**Embeddings:** `text-embedding-004` (768 dimensions)  
**Generation:** `gemini-1.5-flash` (128K context)

### Cost Analysis

Assuming 1000 queries/day with average 3K tokens/query:
- Input tokens: 3M/day = 90M/month
- Cost: 90M × $0.075 / 1M = **$6.75/month**

Compare to OpenAI GPT-4-turbo:
- Same usage: 90M × $10 / 1M = **$900/month**

**Savings: ~$890/month (99% reduction)**

## Consequences

### Positive

- ✅ Minimal infrastructure costs during MVP
- ✅ Fast iteration with generous free tier
- ✅ Single vendor for embeddings + generation
- ✅ Google Cloud reliability and uptime
- ✅ Simple migration path if needed (abstraction via Strategy Pattern)

### Negative

- ❌ Vendor lock-in (mitigated by clean architecture)
- ❌ Quality not quite at GPT-4 level (acceptable for MVP)
- ❌ Less mature ecosystem than OpenAI

### Mitigation Strategies

1. **Architecture:** Use `LLMService` and `EmbeddingService` protocols (see ADR-004)
2. **Monitoring:** Track response quality metrics to detect degradation
3. **Fallback:** Keep OpenAI integration code ready for A/B testing
4. **Cost Alerts:** Set up budget alerts in Google Cloud Console

## Follow-up Actions

- [x] Implement `GoogleLLMService` with Gemini Flash
- [x] Implement `GoogleEmbeddingService` with text-embedding-004
- [ ] Add response quality monitoring dashboard
- [ ] Create cost tracking alerts
- [ ] Document model upgrade path

## References

- [Gemini API Pricing](https://ai.google.dev/pricing)
- [Gemini 1.5 Flash Overview](https://deepmind.google/technologies/gemini/flash/)
- [Text Embeddings Guide](https://ai.google.dev/gemini-api/docs/embeddings)
- RAG Corp: `services/rag-api/app/infrastructure/services/google_llm_service.py`

---

**Last Updated:** 2025-12-29  
**Superseded By:** None
