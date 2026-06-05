---
type: official-open-note
status: canon_ready
source_id: official_docs.cross_check.applied_ml_ch7
date: 2026-05-26
---

# Cross-Check: Applied ML & AI for Engineers — Chapter 7 (Operationalizing ML Models)

Canonical docs corroboration covering deployment strategies for ONNX, Flask/FastAPI REST serving, Docker/containerization, ML.NET, and ONNX Runtime cross-platform availability.

---

## 1. ONNX (Open Neural Network Exchange)

- **Canonical URL:** https://onnxruntime.ai/docs/
- **GitHub:** https://github.com/microsoft/onnxruntime (200 OK, title: "ONNX Runtime: cross-platform, high performance ML inferencing and training accelerator")
- **skl2onnx (sklearn-onnx):** https://onnx.ai/sklearn-onnx/ (title: "sklearn-onnx 1.20.0 documentation")
  - ⚠️ The URL `https://skl2onnx.readthedocs.io/` is **dead** (403 Forbidden via HEAD, 404 via curl). The canonical docs now live at **`https://onnx.ai/sklearn-onnx/`** (GitHub: onnx/sklearn-onnx).

**What official docs say:**
- ONNX Runtime is a cross-platform inference and training accelerator. Models from PyTorch, TensorFlow/Keras, scikit-learn, LightGBM, XGBoost can be converted to ONNX format.
- The sklearn-onnx package converts scikit-learn pipelines to ONNX format via `skl2onnx.to_onnx()`. It supports most sklearn estimators and transformers.
- Export/import contract: trained sklearn model → ONNX graph protobuf (.onnx) → loaded by onnxruntime `InferenceSession` for inference.
- Cross-language runtime semantics: the ONNX graph is language-agnostic; each runtime binding (Python, C++, C#, Java, JS) loads the same `.onnx` file and executes the same computation graph.

### Nuance for the chapter:
- The chapter should cite `onnx.ai/sklearn-onnx/` (not the dead readthedocs URL).
- ONNX opset versioning matters: sklearn-onnx 1.20 supports opset up to ~21; older models may need conversion with a specific opset.
- Not every sklearn estimator is supported — the docs maintain a support matrix on the sklearn-onnx site.

---

## 2. Flask REST API Deployment for ML

- **Canonical URL (Flask):** https://flask.palletsprojects.com/en/stable/deploying/
- **Canonical URL (FastAPI):** https://fastapi.tiangolo.com/deployment/
- **Canonical URL (BentoML):** https://docs.bentoml.com/en/latest/

**What official docs say:**
- **Flask:** "Do not use the development server when deploying to production." Production requires a WSGI server (Gunicorn, Waitress, uWSGI, gevent) and a reverse proxy (nginx, Apache httpd). Flask is a WSGI application — a WSGI server converts HTTP requests to WSGI environ.
- **FastAPI:** ASGI-native, supports async, auto-generated OpenAPI docs. Deployment strategies include Gunicorn+Uvicorn workers, containers, and serverless. Claims higher throughput than Flask for I/O-bound ML inference workloads due to async support.
- **BentoML:** Purpose-built for ML model serving. Defines a "Bento" (model + code + dependencies), serves via REST/gRPC, and supports containerization, Kubernetes, and cloud deployment natively.

### Nuance for the chapter:
- Flask is adequate for simple serving but not optimized for ML — every request creates a fresh `InferenceSession` unless explicitly cached. FastAPI's async support is better for concurrent ML inference.
- BentoML is a stronger production alternative than raw Flask: it handles model lifecycle, batching, and autoscaling out of the box.
- The chapter should recommend FastAPI over Flask for new ML serving APIs, and BentoML for production-grade deployment.

---

## 3. Docker/Containerization for ML Models

- **Canonical URL (Kubernetes Workloads):** https://kubernetes.io/docs/concepts/workloads/
- **Canonical URL (MLflow):** https://mlflow.org/docs/latest/index.html
- **Canonical URL (Docker):** No single "ML guide" page found (https://docs.docker.com/guides/machine-learning/ returns 404). General Docker docs apply.

**What official docs say:**
- **Kubernetes:** Workload resources (Deployments, StatefulSets, Jobs) are the standard abstraction for running containerized ML inference services. Pod autoscaling (HPA) based on CPU/memory or custom metrics is standard practice.
- **MLflow:** Provides `mlflow models serve` (REST API on /invocations), pyfunc flavor, and model registry with stage transitions. Containerized deployment to SageMaker, Azure, and Kubernetes is built in.
- **MLOps standard pattern:** Docker image with model artifact baked in or mounted → Kubernetes Deployment → Service (ClusterIP/LoadBalancer) → Ingress → HPA for autoscaling.

### Nuance for the chapter:
- The chapter should cover multi-stage Docker builds for ML: build stage (install dependencies) → runtime stage (slim image with only onnxruntime/gunicorn).
- Model size management is critical: large DL models (GB+) should use volume mounts or object storage, not baked into the image.
- GPU-aware scheduling (nvidia-device-plugin) is required for GPU inference on Kubernetes.

---

## 4. ML.NET

- **Canonical URL:** https://learn.microsoft.com/en-us/dotnet/machine-learning/ (200 OK, title: "ML.NET documentation")
- **Save/Load models:** https://learn.microsoft.com/en-us/dotnet/machine-learning/how-to-guides/save-load-machine-learning-models-ml-net
- **Predictions:** https://learn.microsoft.com/en-us/dotnet/machine-learning/how-to-guides/machine-learning-model-predictions-ml-net
- **How it works:** https://learn.microsoft.com/en-us/dotnet/machine-learning/how-does-mldotnet-work

**What official docs say:**
- **IDataView:** Central data abstraction. "In ML.NET data is represented by IDataView objects." It's an immutable, lazy-evaluated, schema-typed data transformation pipeline.
- **Pipeline API:** Build pipelines via `mlContext.Transforms` and `mlContext.BinaryClassification/Training`. Pipeline is an `EstimatorChain<ITransformer>`. Calling `Fit()` returns an `ITransformer`.
- **Model persistence:** Models saved as **`.zip` files** via `mlContext.Model.Save(trainedModel, data.Schema, "model.zip")`. Loaded with `mlContext.Model.Load("model.zip", out schema)`.
- **PredictionEngine patterns:**
  - `PredictionEngine<TSrc, TDst>` for single predictions (not thread-safe).
  - `PredictionEnginePool<TSrc, TDst>` (from `Microsoft.Extensions.ML`) provides thread-safe pooling via `ObjectPool`, recommended for web apps.
  - For batch predictions, use `ITransformer.Transform()` on an `IDataView`.
  - Loading: `ITransformer predictionPipeline = mlContext.Model.Load("model.zip", out predictionPipelineSchema);`
- **ONNX interop:** ML.NET can also save/load ONNX models directly.

### Nuance for the chapter:
- The chapter must emphasize that `PredictionEngine` is **not thread-safe** and `PredictionEnginePool` is the correct pattern for production ASP.NET Core apps.
- The `.zip` format is specific to ML.NET's internal serializer — it's not interchangeable with other frameworks.
- ML.NET pipelines separate data preparation transforms from the trained model, which can be saved independently.

---

## 5. ONNX Runtime Cross-Platform Availability

- **Canonical URL (API docs):** https://onnxruntime.ai/docs/api/
- **Install docs:** https://onnxruntime.ai/docs/install/

**What official docs say (verified):**
ONNX Runtime officially supports these language bindings:

| Language   | Docs URL                                        |
|------------|-------------------------------------------------|
| Python     | /docs/api/python/index.html                     |
| C/C++      | /docs/api/c/ (C API docs at genai/api/c.html)   |
| C#         | /docs/api/csharp/ (C# API docs)                 |
| Java       | /docs/api/java/index.html                       |
| JavaScript | /docs/api/js/index.html                         |
| Objective-C| /docs/api/objectivec/index.html                 |

On the **install page**, the docs list: "C#/C/C++/WinML Installs", "JavaScript Installs", "Install on iOS", "Install on Android", plus a full "Inference install table for all languages."

**What this means:**
- The ONNX Runtime delivers the **same computation graph semantics** across all supported languages — a model exported once runs identically on any binding.
- This is the core value proposition: write once, deploy anywhere (cloud, edge, mobile, web browser via JS/WebAssembly).
- Chapter 7 should emphasize this cross-platform portability as a key differentiator vs. framework-specific serving (e.g., PyTorch Serve, TF Serving).

### Correction/nuance for the chapter:
- ONNX Runtime also supports **Objective-C** (iOS), which the chapter may omit.
- The chapter should distinguish between ONNX (the interchange format standard) and ONNX Runtime (the execution engine) — they are separate projects under the LF AI & Data Foundation.
- Windows ML (WinML) is a Windows-specific ONNX Runtime integration, not a separate runtime.

---

## URL Verification Summary

| URL                                           | Status   | Notes                                 |
|-----------------------------------------------|----------|---------------------------------------|
| https://onnxruntime.ai/docs/                  | ✅ 200   | Canonical ONNX Runtime docs           |
| https://github.com/microsoft/onnxruntime      | ✅ 200   | GitHub repo                           |
| https://skl2onnx.readthedocs.io/              | ❌ 403/404| **Dead link** — use onnx.ai/sklearn-onnx/ instead |
| https://learn.microsoft.com/en-us/dotnet/machine-learning/ | ✅ 200 | ML.NET documentation hub |

## Key Corrections Summary

1. **skl2onnx URL is dead** — redirect to https://onnx.ai/sklearn-onnx/
2. **Flask production** requires WSGI server + reverse proxy, not the dev server
3. **FastAPI/BentoML** are stronger production alternatives than raw Flask for ML
4. **PredictionEngine** is not thread-safe — use PredictionEnginePool in production
5. **ONNX Runtime** supports Objective-C (iOS) in addition to C/C++/C#/Java/JS
6. **ML.NET .zip format** is internal-only, not portable across frameworks