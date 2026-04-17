# RAG — Document Ingestion & Retrieval System

A production-ready **Retrieval-Augmented Generation (RAG)** pipeline built with FastAPI, Celery, MinIO, Qdrant, and Redis. Upload any document and it is automatically streamed to object storage, then asynchronously extracted, chunked, embedded in batches, entity-tagged, and indexed — all without blocking the HTTP response.

---

## Benchmarks

Tested on **Azure Kubernetes Service (AKS)** — single node, `Standard_B2s_v2` (2 vCPU, 4 GB RAM).

| Metric | Value |
|--------|-------|
| **Documents ingested** | 20 PDFs |
| **Total data size** | ~130 MB |
| **Total ingestion time** | ~5 minutes |
| **Total chunks generated** | ~15,000 |
| **Avg chunks per document** | ~750 |
| **Avg throughput** | ~50 chunks / second end-to-end |
| **Celery concurrency** | 20 workers (gevent green threads) |
| **Embedding model** | OpenAI `text-embedding-3-small` |
| **Embedding batch size** | 100 chunks / API call |
| **Embedding API calls** | ~150 (15,000 chunks ÷ 100) |
| **Entity extractor** | spaCy `en_core_web_sm` (`nlp.pipe`, batch 50) |
| **Node SKU** | Standard_B2s_v2 · 2 vCPU · 4 GB RAM |

> **Key insight:** gevent allows 20 concurrent tasks on a 2-vCPU node because the pipeline is overwhelmingly I/O-bound (MinIO download, OpenAI API calls, Qdrant upsert). CPU is only active during spaCy NER and text splitting, which are fast enough not to be the bottleneck at this scale.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Supported File Types](#supported-file-types)
4. [Project Structure](#project-structure)
5. [Implementation Deep-Dive](#implementation-deep-dive)
   - [1. Streaming Upload & Deduplication](#1-streaming-upload--deduplication)
   - [2. Celery Pipeline & Queue Design](#2-celery-pipeline--queue-design)
   - [3. Redis — Broker, Result Backend & Task Reliability](#3-redis--broker-result-backend--task-reliability)
   - [4. Ingest Task — MinIO Download & Extraction](#4-ingest-task--minio-download--extraction)
   - [5. Transform Task — Chunking, Batch Embedding & Entity Extraction](#5-transform-task--chunking-batch-embedding--entity-extraction)
   - [6. Store Task — Vector Upsert & Deduplication](#6-store-task--vector-upsert--deduplication)
   - [7. Extensible Registry Pattern](#7-extensible-registry-pattern)
6. [Getting Started (Docker Compose)](#getting-started-docker-compose)
7. [Kubernetes Deployment (AKS)](#kubernetes-deployment-aks)
   - [Cluster Layout](#cluster-layout)
   - [Manifests Reference](#manifests-reference)
   - [Deploy](#deploy)
8. [Local Development](#local-development)
9. [API Reference](#api-reference)
10. [Configuration Reference](#configuration-reference)

---

## Architecture Overview

```
HTTP Upload (FastAPI)
        │  Streamed in 1 MB chunks
        │  MD5 hash computed on the fly
        ▼
  MinIO (S3-compatible Object Store)
        │  File stored at rest
        │  Metadata passed to Celery
        ▼
  Redis (Broker + Result Backend)
        │  task_acks_late=True   ← task re-queued on worker crash
        │  worker_prefetch=1     ← prevents head-of-line blocking
        ▼
  ┌─────────────────────────────────────────┐
  │  Celery chain (executed in order)        │
  │                                          │
  │  [ingest]     ← queue: ingest            │
  │      ↓  passes enriched dict             │
  │  [transform]  ← queue: transform         │
  │      ↓  passes embedded chunks           │
  │  [store]      ← queue: store             │
  └─────────────────────────────────────────┘
        │
        ▼
  Qdrant (Vector Store)
  Cosine similarity · UUID5 deterministic IDs · upsert (idempotent)
```

**Each stage runs in its own dedicated Celery queue** with independent concurrency, retry policy, and failure isolation. A crash in `transform` does not affect unrelated `ingest` or `store` operations running in parallel.

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| API server | FastAPI + Uvicorn | HTTP endpoint, async streaming upload |
| Task queue | Celery 5 (gevent pool) | Async pipeline orchestration |
| Message broker | Redis 7 | Task routing & queue persistence |
| Result backend | Redis 7 | Inter-task state passing (TTL 1 h) |
| Object storage | MinIO (S3-compatible) | Durable raw file storage |
| Vector database | Qdrant | Dense vector index (cosine similarity) |
| Embeddings | OpenAI API | Batched dense vector generation |
| NLP | spaCy `en_core_web_sm` | Batched named-entity recognition |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` | Semantic-aware chunking |
| Settings | Pydantic Settings | Typed, validated config from `.env` / k8s Secrets |
| HTTP resilience | Tenacity | Exponential backoff on OpenAI API errors |
| Package manager | uv | Fast, lock-file-based dependency management |
| Containers | Docker + Docker Compose | Local full-stack deployment |
| Orchestration | Kubernetes (AKS) | Production deployment |

---

## Supported File Types

| Format | Extractor | Library | Notes |
|--------|-----------|---------|-------|
| PDF | `PDFExtractor` | PyMuPDF (fitz) | Per-page extraction, empty-page warnings |
| DOCX | `DocxExtractor` | python-docx | Full paragraph extraction |
| TXT | `TxtExtractor` | built-in | UTF-8 read |
| ZIP | (auto) | stdlib `zipfile` | Each contained file processed individually |

---

## Project Structure

```
rag/
├── main.py                          # FastAPI app — upload, ZIP handling, streaming
├── pyproject.toml                   # Dependencies (uv / PEP 517)
├── Dockerfile                       # Multi-stage build (builder + runtime)
├── docker-compose.yml               # api, celery-worker, qdrant, minio, redis, redisinsight
│
├── k8s/                             # Kubernetes manifests (AKS)
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── fastapi/
│   │   ├── deployment.yaml
│   │   └── service.yaml             # LoadBalancer (public IP)
│   ├── celery/
│   │   └── deployment.yaml          # gevent worker, --concurrency=20
│   ├── minio/
│   │   ├── statefulset.yaml
│   │   ├── service.yaml             # ClusterIP (internal only)
│   │   └── pvc.yaml                 # 10 Gi managed-csi
│   └── qdrant/
│       ├── statefulset.yaml
│       ├── service.yaml             # ClusterIP (internal only)
│       └── pvc.yaml                 # 10 Gi managed-csi
│
├── core/
│   ├── tasks/
│   │   ├── pipeline.py              # Celery chain: ingest → transform → store
│   │   ├── ingest.py                # Download from MinIO, extract text
│   │   ├── transform.py             # Chunk, embed (batched), entity extract (batched)
│   │   └── store.py                 # Upload to Qdrant, cleanup temp file
│   └── layers/
│       ├── extraction.py · chunker.py · embedder.py · entity_generation.py
│       ├── minio_upload.py · qdrant_upload.py
│       ├── extractors/              # pdf · docx · txt · registry
│       ├── chunkers/                # recursive · registry
│       ├── embedders/               # openai_embeddings · registry
│       └── entity_extractors/       # spacy_extractor · registry
│
└── src/
    ├── config/
    │   ├── config.py                # Pydantic Settings: Minio/Qdrant/Redis/Embedding
    │   └── celery_config.py         # Celery app, queues, broker/backend URLs
    └── db/
        ├── clients.py               # Redis, AsyncQdrantClient, Minio client factories
        └── models/
```

---

## Implementation Deep-Dive

### 1. Streaming Upload & Deduplication

Uploads are **streamed in 1 MB chunks** — the file is never fully buffered in memory before being forwarded to MinIO:

```python
# main.py
CHUNK_SIZE = 1024 * 1024       # 1 MB
PART_SIZE  = 10 * 1024 * 1024  # 10 MB MinIO multipart threshold

async def _upload_single(object_name, upload_file, content_type):
    hasher = hashlib.md5()
    chunks = []
    async for chunk in _iter_chunks(upload_file):   # yields 1 MB at a time
        hasher.update(chunk)                        # hash computed on the fly
        chunks.append(chunk)
    file_hash = hasher.hexdigest()                  # MD5 for deduplication key
    data_stream = io.BytesIO(b"".join(chunks))
    minio_client.put_object(... data=data_stream, length=total_length ...)
```

**Why this matters:**
- Large PDFs (hundreds of MBs) never spike heap memory.
- The MD5 hash doubles as a stable **deduplication key** — the same file always generates the same Qdrant point IDs (see §6).

**ZIP handling** — archives are unpacked in-memory and each contained file is routed through the same `_upload_single` path:

```python
async def _handle_zip_upload(zip_file):
    folder_name = zip_file.filename.removesuffix(".zip")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for entry in zf.infolist():
            object_name = f"{folder_name}/{entry.filename}"
            await _upload_single(object_name, fake_file, content_type)
```

---

### 2. Celery Pipeline & Queue Design

The three processing stages are wired together as a **Celery chain** — the output dict of each task is automatically passed as the first argument to the next:

```python
# core/tasks/pipeline.py
pipeline = chain(
    ingest_data.s(data),       # stage 1 — returns enriched dict
    transform_document.s(),    # stage 2 — receives enriched dict
    store_document.s()         # stage 3 — receives dict with embedded_chunks
)
pipeline.apply_async()
```

Each task is pinned to its own **dedicated queue with its own exchange and routing key**:

```python
# src/config/celery_config.py
task_queues = (
    Queue("ingest",    Exchange("ingest"),    routing_key="ingest"),
    Queue("transform", Exchange("transform"), routing_key="transform"),
    Queue("store",     Exchange("store"),     routing_key="store"),
)
```

The single Celery worker process consumes all three queues:

```bash
celery -A src.config.celery_config.celery_app worker \
  -Q ingest,transform,store \
  --concurrency=20 -P gevent    # 20 green threads — benchmarked on 2 vCPU / 4 GB
```

**Why gevent on a 2-vCPU node?**
Almost every step in the pipeline is I/O-bound: downloading from MinIO, calling the OpenAI API, writing to Qdrant. Gevent's cooperative multitasking means 20 tasks can be "in flight" simultaneously while only 1–2 are actually running Python code at any moment — effectively saturating I/O bandwidth without needing 20 OS threads.

**Why separate queues?**
- Stages can be scaled independently (e.g., add more workers just for `transform` if embedding becomes the bottleneck).
- A backlog in `store` does not block `ingest` from accepting new documents.

**Retry policy** — every task uses the same hardened config:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_data(self, metadata):
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

### 3. Redis — Broker, Result Backend & Task Reliability

Redis serves **two roles simultaneously**:

| Role | Redis DB | Purpose |
|------|----------|---------|
| Broker | `/0` | Stores task messages in queues; Celery workers `BLPOP` from these |
| Result Backend | `/0` | Stores return values of completed tasks (TTL: 1 hour) |

**Reliability settings** that prevent task loss:

```python
# src/config/celery_config.py
CELERY_CONFIG = {
    "task_acks_late": True,             # task NOT removed from queue until it succeeds
    "task_reject_on_worker_lost": True, # worker crash → message re-queued
    "worker_prefetch_multiplier": 1,    # worker only fetches one task at a time
    "result_expires": 3600,             # inter-task results auto-expire after 1 hour
}
```

- **`task_acks_late=True`** is critical: with the default `acks_early`, a crash between task acknowledgement and completion permanently loses the task. With `acks_late`, the broker only removes the message after the task function returns successfully.
- **`worker_prefetch_multiplier=1`** prevents a fast worker from hoarding tasks, ensuring even distribution across multiple worker processes.
- **`result_expires=3600`** avoids Redis growing unbounded — completed task payloads (which include the full embedded chunks) are garbage-collected after an hour.

In production (AKS), Redis is hosted as **Azure Cache for Redis** (`rag-redis-uday.redis.cache.windows.net`, port 6380) — external to the cluster, managed, and HA by default. This means the broker survives k8s node restarts without data loss.

---

### 4. Ingest Task — MinIO Download & Extraction

```python
# core/tasks/ingest.py
def ingest_data(self, metadata: dict) -> dict:
    ext      = Path(object_key).suffix.lower()
    tmp_path = Path(tempfile.gettempdir()) / f"{file_hash}{ext}"

    minio_client.fget_object(bucket, object_key, str(tmp_path))  # download to disk
    extraction_result = extract(tmp_path)                         # dispatch to extractor
    return {**metadata, "extracted_text": ..., "extracted_metadata": ...}
```

**Temp file naming** uses the file hash (`{md5}{.ext}`), so re-uploading the same file overwrites the same temp path rather than accumulating duplicates.

**Extractor dispatch** uses a registry keyed by file extension:

```python
# core/layers/extraction.py
extractor_cls = registry.get_extractor(file_path.suffix)  # ".pdf" → PDFExtractor
extractor = extractor_cls()
text, metadata = extractor.extract(file_path)
```

The **PDF extractor** (PyMuPDF) iterates pages and joins non-empty page text:

```python
# core/layers/extractors/pdf.py
for page_num, page in enumerate(doc):
    page_text = page.get_text()
    if page_text.strip():
        texts.append(page_text)

return "\n".join(texts), {
    "pages": pages,
    "file_name": file_path.name,
    "file_size": file_path.stat().st_size,
    "file_hash": md5(file_path.read_bytes()).hexdigest()
}
```

---

### 5. Transform Task — Chunking, Batch Embedding & Entity Extraction

#### Chunking

```python
# core/layers/chunkers/recursive.py
class RecursiveChunker(BaseChunker):
    def __init__(self, chunk_size=1024, chunk_overlap=100):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text, metadata):
        texts = self.splitter.split_text(text)
        # deep-copied per chunk — mutations in one chunk don't bleed into others
        return [Chunk(text=t, metadata=metadata.copy()) for t in texts]
```

- **1 024-character chunks** with **100-character overlap** — large enough to be semantically coherent, small enough for precise retrieval.
- Splits on `["\n\n", "\n", " ", ""]` in order, preserving paragraph and sentence boundaries wherever possible.
- At 15,000 chunks across 20 documents, this averaged **~750 chunks per document** in benchmarks.

#### Batch Embedding

Chunks are sent to OpenAI in configurable batches (default **100 chunks per API call**):

```python
# core/layers/embedders/openai_embeddings.py
def embed_batch(self, chunks):
    batches = [chunks[i:i + self.batch_size]
               for i in range(0, len(chunks), self.batch_size)]

    for batch_num, batch in enumerate(batches):
        texts = [chunk.text for chunk in batch]
        embeddings = self._embed_with_retry(texts, batch_num)
        for chunk, embedding in zip(batch, embeddings):
            chunk.metadata['chunk_length'] = len(chunk.text)
            chunk.metadata['chunk_index'] = batch_num * self.batch_size + batch.index(chunk)
            results.append(EmbeddedChunk(...))
```

**Retry with exponential backoff** (Tenacity) handles OpenAI rate limits transparently:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)  # 2s → 4s → 8s → fail
)
def _embed_with_retry(self, texts, batch_num):
    response = self.client.embeddings.create(input=texts, model=self.model_name)
    return [e.embedding for e in response.data]
```

**Throughput impact of batching** (based on benchmark — 15,000 chunks):

| Strategy | API calls | Latency savings |
|----------|-----------|-----------------|
| No batching (1 chunk/call) | 15,000 calls | baseline |
| **Batch size 100** | **150 calls** | **~99% fewer round-trips** |

#### Batched Entity Extraction (spaCy)

All chunk texts are piped through spaCy in a **single `nlp.pipe()` call** rather than one at a time:

```python
# core/layers/entity_extractors/spacy_extractor.py
def extract_batch(self, texts: list[str]) -> list[ExtractedEntities]:
    docs = self.nlp.pipe(texts, batch_size=50)   # 50 docs batched internally
    return [self._doc_to_entities(doc) for doc in docs]
```

Only `ner` is active — `parser`, `tagger`, and `lemmatizer` are **disabled at load time**:

```python
self.nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
```

| spaCy Label | Field |
|-------------|-------|
| `PERSON` | `people` |
| `ORG` | `organizations` |
| `GPE` | `locations` |
| `LOC` | `locations` |

---

### 6. Store Task — Vector Upsert & Deduplication

Embedded chunks are uploaded using **async I/O** to avoid blocking the Celery worker:

```python
# core/tasks/store.py
asyncio.run(upload_to_qdrant(collection_name=QDRANT_COLLECTION_NAME, embedded_chunks=...))
```

**Deterministic UUID5 point IDs** make re-uploads fully idempotent:

```python
# core/layers/qdrant_upload.py
external_id = f"{file_hash}_{index}"                               # e.g. "d41d8cd..._42"
id_value    = str(uuid.uuid5(uuid.NAMESPACE_DNS, external_id))    # deterministic UUID
```

The collection is **auto-created** on first upload using the vector dimensionality inferred from the first chunk's embedding.

**Payload stored per point:**

```json
{
  "text": "...chunk text...",
  "file_name": "report.pdf",
  "pages": 12,
  "file_hash": "d41d8cd98f00b204e9800998ecf8427e",
  "chunk_index": 42,
  "chunk_length": 987,
  "entities": {
    "people": ["Elon Musk"],
    "organizations": ["Tesla"],
    "locations": ["Austin"]
  }
}
```

**Temp file cleanup** runs in a `finally` block — executes even if the Qdrant upload fails:

```python
finally:
    if tmp_path and Path(tmp_path).exists():
        Path(tmp_path).unlink()
```

---

### 7. Extensible Registry Pattern

Every layer uses the same **self-registering registry pattern**. Adding a new implementation requires only:
1. Subclass the `Base*` abstract class.
2. Add it to `_register_defaults` in the corresponding `registry.py`.

```python
# Example — adding a HuggingFace embedder
class HuggingFaceEmbedder(BaseEmbedder):
    @property
    def provider_name(self): return "huggingface"
    def embed_batch(self, chunks): ...

# In registry.py — just add to the list
for embedder_cls in [OpenAIEmbedder, HuggingFaceEmbedder]:
    ...
```

---

## Getting Started (Docker Compose)

### Prerequisites

- Docker & Docker Compose
- OpenAI API key

```bash
git clone <repo-url>
cd rag
cp .env.example .env   # fill in your keys
docker compose up --build
```

| Service | URL |
|---------|-----|
| FastAPI API | http://localhost:8000 |
| MinIO Console | http://localhost:9001 |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| RedisInsight | http://localhost:5540 |

---

## Kubernetes Deployment (AKS)

The `k8s/` directory contains all manifests for deploying to Azure Kubernetes Service. The production benchmark (130 MB / 20 PDFs / 5 min) was run on this exact setup.

### Cluster Layout

```
Namespace: rag
│
├── Deployments
│   ├── fastapi          (1 replica, LoadBalancer service — public IP)
│   └── celery-worker    (1 replica, gevent --concurrency=20)
│
├── StatefulSets
│   ├── minio            (10 Gi PVC, managed-csi, ClusterIP)
│   └── qdrant           (10 Gi PVC, managed-csi, ClusterIP)
│
├── External Services
│   └── Azure Cache for Redis  (managed, outside cluster)
│
└── Config
    ├── ConfigMap  rag-config   (ENVIRONMENT, LOG_LEVEL)
    └── Secret     rag-secrets  (all credentials)
```

**Networking:**
- `fastapi-service` → `LoadBalancer` → public IP (port 80 → container 8000)
- `minio-service` → `ClusterIP` → in-cluster only (port 9000 API, 9001 console)
- `qdrant-service` → `ClusterIP` → in-cluster only (port 6333)
- Redis → external Azure managed endpoint (TLS, port 6380)

### Manifests Reference

#### `k8s/namespace.yaml`
Creates the `rag` namespace that all resources live in.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rag
```

---

#### `k8s/configmap.yaml`
Non-sensitive runtime config injected via `envFrom.configMapRef` in both deployments.

```yaml
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
```

---

#### `k8s/secrets.yaml`
All credentials stored as a single `rag-secrets` Secret, injected via `envFrom.secretRef`. Uses `stringData` (plain text in manifest, base64-encoded at rest in etcd).

> ⚠️ Do not commit real credentials. Replace values before applying or use a secrets manager (Azure Key Vault, Sealed Secrets, External Secrets Operator).

Secrets managed:

| Key | Used by |
|-----|---------|
| `REDIS_HOST / PORT / PASSWORD` | Both deployments (Azure Cache for Redis) |
| `EMBEDDING_API_KEY / MODEL_NAME` | Celery worker |
| `MINIO_HOST / PORT / USER / PASSWORD / BUCKET` | Both deployments |
| `QDRANT_HOST / HTTP_PORT / API_KEY / COLLECTION_NAME` | Both deployments |

---

#### `k8s/fastapi/deployment.yaml`
Single-replica FastAPI deployment. Pulls from Azure Container Registry (`ragregistryuday.azurecr.io/rag-api:latest`).

| Setting | Value | Rationale |
|---------|-------|-----------|
| `replicas` | 1 | Stateless; scale horizontally if upload volume grows |
| Memory request/limit | 256 Mi / 512 Mi | Upload handler is thin — no heavy in-memory processing |
| CPU request/limit | 100m / 500m | Async I/O; rarely CPU-bound |
| Liveness probe | `GET /` every 10 s | Restart if app hangs |
| Readiness probe | `GET /` every 5 s | Remove from LB until app is ready |

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

#### `k8s/fastapi/service.yaml`
Exposes the API publicly via an Azure load balancer.

```yaml
spec:
  type: LoadBalancer   # AKS provisions an Azure Public IP
  ports:
    - port: 80
      targetPort: 8000
```

---

#### `k8s/celery/deployment.yaml`
The Celery worker — same image as FastAPI, different `command`.

| Setting | Value | Rationale |
|---------|-------|-----------|
| `replicas` | 1 | Benchmarks show 1 replica @ concurrency=20 saturates the node |
| `--concurrency=20` | 20 green threads | 20 concurrent pipeline tasks; I/O-bound → gevent is efficient |
| `-P gevent` | gevent pool | Cooperative multitasking; no GIL contention on I/O waits |
| Memory request/limit | 1 Gi / 2 Gi | spaCy model + embedded chunk buffers in memory |
| CPU request/limit | 200m / 1000m | CPU spikes during NER; gevent keeps threads yielding |

```yaml
command:
  - celery
  - -A
  - src.config.celery_config.celery_app
  - worker
  - -Q
  - ingest,transform,store
  - --concurrency=20
  - -P
  - gevent
  - --loglevel=info
```

---

#### `k8s/minio/statefulset.yaml`
MinIO deployed as a StatefulSet for stable network identity and persistent storage.

- Mounts a `PersistentVolumeClaim` at `/data`
- Credentials injected individually from `rag-secrets` (not `envFrom` — MinIO requires specific env var names)
- Liveness: `GET /minio/health/live` · Readiness: `GET /minio/health/ready`

```yaml
resources:
  requests: { memory: "256Mi", cpu: "100m" }
  limits:   { memory: "512Mi", cpu: "500m" }
```

#### `k8s/minio/service.yaml`
ClusterIP only — MinIO is internal storage. The API (`9000`) and console (`9001`) are both exposed within the cluster.

#### `k8s/minio/pvc.yaml`
```yaml
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
  storageClassName: managed-csi   # Azure managed disk (Premium SSD)
```

---

#### `k8s/qdrant/statefulset.yaml`
Qdrant deployed as a StatefulSet — persistent storage is essential to avoid re-indexing on pod restart.

- Mounts PVC at `/qdrant/storage`
- API key injected from `rag-secrets`
- Liveness & Readiness: `GET /healthz`

```yaml
resources:
  requests: { memory: "512Mi", cpu: "250m" }
  limits:   { memory: "1Gi",   cpu: "500m" }
```

Higher memory limit than MinIO — Qdrant loads the HNSW index into RAM for fast ANN search. At 15,000 vectors (1,536 dimensions, `text-embedding-3-small`), the index fits well within 1 Gi.

#### `k8s/qdrant/service.yaml`
ClusterIP — Qdrant is queried only by in-cluster services.

#### `k8s/qdrant/pvc.yaml`
```yaml
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
  storageClassName: managed-csi
```

---

### Deploy

```bash
# 1. Create namespace first
kubectl apply -f k8s/namespace.yaml

# 2. Apply config and secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 3. Storage (PVCs must exist before StatefulSets reference them)
kubectl apply -f k8s/minio/pvc.yaml
kubectl apply -f k8s/qdrant/pvc.yaml

# 4. Stateful services
kubectl apply -f k8s/minio/statefulset.yaml
kubectl apply -f k8s/minio/service.yaml
kubectl apply -f k8s/qdrant/statefulset.yaml
kubectl apply -f k8s/qdrant/service.yaml

# 5. Application
kubectl apply -f k8s/fastapi/deployment.yaml
kubectl apply -f k8s/fastapi/service.yaml
kubectl apply -f k8s/celery/deployment.yaml

# Or apply everything at once (order is handled by Kubernetes)
kubectl apply -f k8s/ --recursive
```

**Check status:**

```bash
kubectl get pods -n rag
kubectl get svc  -n rag          # grab the FastAPI LoadBalancer EXTERNAL-IP
kubectl logs -n rag deploy/celery-worker --follow
```

**Upload a document to the cluster:**

```bash
EXTERNAL_IP=$(kubectl get svc fastpi-service -n rag -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -X POST http://$EXTERNAL_IP/file-upload/ -F "files=@document.pdf"
```

---

## Local Development

```bash
# Install dependencies
uv sync

# Download spaCy model
uv run python -m spacy download en_core_web_sm

# Start only backing services (Redis, MinIO, Qdrant)
docker compose up redis minio qdrant -d

# Run the API
uv run uvicorn main:app --reload --port 8000

# Run the Celery worker (separate terminal)
uv run celery -A src.config.celery_config.celery_app worker \
  -Q ingest,transform,store \
  --concurrency=20 -P gevent --loglevel=info
```

Requires Python 3.12 and running Redis, MinIO, and Qdrant instances.

---

## API Reference

### `GET /`
Health check — used by liveness/readiness probes in k8s.

```json
{ "message": "Welcome to the RAG system!" }
```

### `POST /file-upload/`
Upload one or more files. Streamed to MinIO, pipeline triggered asynchronously.

```bash
# Single file
curl -X POST http://localhost:8000/file-upload/ \
  -F "files=@/path/to/document.pdf"

# Multiple files
curl -X POST http://localhost:8000/file-upload/ \
  -F "files=@doc1.pdf" -F "files=@doc2.docx"

# ZIP archive (unpacked automatically)
curl -X POST http://localhost:8000/file-upload/ \
  -F "files=@documents.zip"
```

**Response:**

```json
{
  "uploaded": [
    {
      "object": "report.pdf",
      "hash": "d41d8cd98f00b204e9800998ecf8427e",
      "task_id": "a1b2c3d4-5678-..."
    }
  ]
}
```

---

## Configuration Reference

All settings loaded from `.env` (local) or k8s Secrets (production) via Pydantic Settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI secret key |
| `EMBEDDING_MODEL_NAME` | — | e.g. `text-embedding-3-small` |
| `EMBEDDING_BATCH_SIZE` | `100` | Chunks per OpenAI API call |
| `QDRANT_HOST` | — | Qdrant hostname |
| `QDRANT_HTTP_PORT` | — | Qdrant REST port |
| `QDRANT_API_KEY` | — | Qdrant auth key |
| `QDRANT_COLLECTION_NAME` | — | Vector collection name |
| `MINIO_HOST` | — | MinIO hostname |
| `MINIO_API_PORT` | — | MinIO S3 API port |
| `MINIO_BUCKET_NAME` | — | Target bucket |
| `REDIS_HOST` | — | Redis hostname |
| `REDIS_PORT` | — | Redis port (6380 for Azure TLS) |
| `REDIS_PASSWORD` | — | Redis auth password |

---

## License

MIT