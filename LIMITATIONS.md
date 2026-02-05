# System Limitations & Future Improvements

This document clearly states what is intentionally NOT implemented in the current version and provides a realistic roadmap for future development.

---

## What's NOT Included (By Design)

| Feature | Status | Why |
|---------|--------|-----|
| **Real-time Notifications** | Not implemented | Requires WebSocket infrastructure and push notification services (Firebase, APNs) |
| **Mobile Apps** | Web only | Native iOS/Android development is out of scope; web app is responsive |
| **External LLM Integration** | Excluded | RAG answers come ONLY from indexed classroom data - no ChatGPT/Claude to avoid hallucinations |
| **Multi-Language Q&A** | English only | Embedding model (MiniLM) optimized for English |
| **Grade Prediction** | Not implemented | ML predictions require training data and can be misleading |
| **Other LMS Integrations** | Google Classroom only | Canvas, Blackboard, Moodle are future work |
| **File Attachment Analysis** | Metadata only | Parsing PDFs/docs requires OCR infrastructure |
| **Video/Audio Transcription** | Not implemented | Requires transcription service (Whisper, etc.) |
| **Custom Grading Rubrics** | Not implemented | Uses Google Classroom's native grading |
| **Parent/Guardian Portal** | Not implemented | Would require additional role and permissions |
| **Plagiarism Detection** | Not implemented | Requires integration with Turnitin or similar |
| **Live Class Features** | Not implemented | Google Meet integration is separate |

---

## Current Architecture Constraints

### Performance Limits
- **Embedding Model**: all-MiniLM-L6-v2 (384 dimensions) - fast but not the most accurate
- **Vector Store**: ChromaDB - great for development, may need Pinecone/Weaviate at scale
- **Background Jobs**: arq (Redis-based) - works for moderate load, not enterprise scale

### Security Limitations
- **Token Storage**: Encrypted at rest, but in PostgreSQL (not HSM)
- **Rate Limiting**: Basic per-user limits, no advanced throttling
- **Audit Logs**: Stored in database (not SIEM integrated)

### Scalability Notes
- Current design handles ~100 concurrent users comfortably
- For 1000+ users: need read replicas, Redis cluster, CDN for frontend

---

## Realistic Future Roadmap

### Phase 1: Stability (1-2 months after launch)
- [ ] Add comprehensive test coverage (unit + integration)
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Implement proper error tracking (Sentry)
- [ ] Add database migrations workflow (Alembic)

### Phase 2: Features (3-6 months)
- [ ] Real-time notifications via WebSockets
- [ ] Email notification integration (SendGrid/SES)
- [ ] File attachment indexing (PDFs, DOCX)
- [ ] Canvas LMS integration

### Phase 3: Scale (6-12 months)
- [ ] Migrate to managed vector database (Pinecone)
- [ ] Add Kubernetes deployment configuration
- [ ] Implement caching CDN for frontend
- [ ] Multi-tenant architecture

### Phase 4: Intelligence (12+ months)
- [ ] Upgrade to larger embedding model
- [ ] Add optional LLM summarization (with clear disclaimers)
- [ ] Predictive analytics (with proper ML validation)
- [ ] Multi-language support

---

## Honest Assessment

### What This System Does Well
1. **Syncs classroom data reliably** - handles pagination, rate limits, errors
2. **Answers questions from actual content** - no hallucination, sources cited
3. **Explains performance simply** - plain English, not academic jargon
4. **Respects user privacy** - tokens encrypted, minimal data collection

### What Could Be Better
1. **First-time sync is slow** - indexing large courses takes minutes
2. **Q&A quality depends on indexed content** - garbage in, garbage out
3. **No offline support** - requires internet connection
4. **Limited customization** - reminder timing, report formats are fixed

---

## Technical Debt Acknowledged

| Item | Priority | Effort |
|------|----------|--------|
| Add TypeScript strict mode to frontend | Medium | 2-3 days |
| Improve error messages in UI | Medium | 1 day |
| Add database connection pooling monitoring | Low | 1 day |
| Replace manual queries with repository pattern | Low | 1 week |
| Add OpenAPI schema validation tests | Low | 2 days |

---

## Dependencies & Risks

### External Dependencies
- **Google Classroom API**: If Google changes API, sync breaks
- **sentence-transformers**: Model updates may change embedding dimensions
- **ChromaDB**: Breaking changes in major versions

### Mitigation Strategies
- Pin dependency versions in requirements.txt
- Abstract external APIs behind adapter interfaces
- Monitor Google Classroom API changelog

---

*Last updated: February 2026*
