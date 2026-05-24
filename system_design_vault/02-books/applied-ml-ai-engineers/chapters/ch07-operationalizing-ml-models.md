# Chapter 7: Operationalizing Machine Learning Models

## Overview

Operationalization is the process of making Python-trained ML models consumable from any platform, any language, and any deployment target. The chapter presents four strategies: pickle serialization, REST API wrapping (Flask), Docker containerization, and ONNX cross-platform export. It also covers writing models directly in C# with ML.NET and integrating Python models into Excel via Xlwings.

## Strategies Overview

```mermaid
flowchart TD
    A[Trained Python Model] --> B{Consumption target?}
    B --> C[Python client]
    B --> D[Non-Python client]
    B --> E[Excel]
    
    C --> F[Pickle .pkl]
    D --> G{Approach?}
    G --> H[Flask REST API]
    G --> I[ONNX .onnx file]
    H --> J[Any HTTP-speaking client<br>C#, Java, JS...]
    I --> K[ONNX Runtime<br>in C, C++, C#, Java, JS, Obj-C]
    
    F --> L[Python pickle.load]
    
    E --> M[Xlwings UDF]
    M --> N[Excel cell =analyze_text(A1)]
```

## Strategy 1: Pickle (Python → Python)

The simplest path: serialize trained Scikit models (including full pipelines with transformers) to `.pkl` files using `pickle.dump`, then deserialize with `pickle.load` in any Python client.

```python
# Save
pickle.dump(model, open('titanic.pkl', 'wb'))

# Load & predict
model = pickle.load(open('titanic.pkl', 'rb'))
model.predict_proba(female)[0][1]
```

**Pipeline support**: Scikit's `make_pipeline` bundles transformers (e.g., CountVectorizer) with estimators into a single picklable object.

**Caveat—large pickle files**: CountVectorizer stores the entire vocabulary in the `.pkl` file. A 50 MB file can be reduced to ~8 MB by switching to `HashingVectorizer` (no vocabulary stored).

**Version lock**: Models pickled with one Scikit version cannot be unpickled with another. Requires careful version management across environments—a driver for MLOps tooling.

## Strategy 2: Flask REST API (Python → Any Language)

Wrap the model in a Flask web service exposing a REST endpoint:

```python
@app.route('/analyze', methods=['GET'])
def analyze():
    text = request.args.get('text')
    score = pipe.predict_proba([text])[0][1]
    return str(score)
```

- Any client generating HTTP(S) requests can call the model.
- Input/output can use JSON POST bodies for complex data.
- **Performance penalty**: ~2 seconds per round-trip locally vs. 0.001 seconds for ONNX.
- Requires Python runtime + all dependencies on the server.

## Strategy 3: Docker Containers

Containerize the Flask app + model for portable deployment. A `Dockerfile` specifies:
- Python runtime
- Required packages (Flask, numpy, scikit-learn)
- App files and model
- Exposed port
- Entry point

```dockerfile
FROM python:3.8
RUN pip install flask numpy scipy scikit-learn && mkdir /app
COPY app.py /app
COPY sentiment.pkl /app
WORKDIR /app
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["app.py"]
```

Build: `docker build -t sentiment-server .`  
Deploy to cloud registries (Azure Container Registry, AWS ECR) for global accessibility. Benefits: no host-side Python installation needed, dependency isolation, easy scaling.

## Strategy 4: ONNX (Cross-Platform, Direct)

**Open Neural Network Exchange** is a platform-agnostic model format. Originally for deep-learning frameworks (TensorFlow ↔ PyTorch), now also supports Scikit-Learn via `skl2onnx`.

```python
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

initial_type = [('string_input', StringTensorType([None, 1]))]
onnx_model = convert_sklearn(pipe, initial_types=initial_type)
with open('sentiment.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
```

Consumption in C#:

```csharp
var session = new InferenceSession("sentiment.onnx");
var output = session.Run(input);
```

**Performance**: ONNX runtime averages 0.001 seconds vs. 2+ seconds for Flask—a 2,000x speedup. No web server overhead.

**Available runtimes**: Python, C, C++, C#, Java, JavaScript, Objective-C. Platforms: Windows, Linux, macOS, Android, iOS.

**Key insight**: ONNX is a game-changer for projecting Python ML models to other languages and platforms.

## Strategy 5: ML.NET (Write Models in C# Directly)

Microsoft's open-source, cross-platform ML framework for .NET developers:

- Equivalent to Scikit-Learn in capability
- Handles datasets larger than memory via `IDataView` (SQL-like cursor, not in-memory DataFrame)
- In benchmarks: trained 6x faster than Scikit, 10x faster than H2O on a 9 GB dataset
- Supports transfer learning and ONNX model loading
- Build models with pipelines similar to Scikit

```csharp
var context = new MLContext(seed: 0);
var pipeline = context.Transforms.Text.FeaturizeText(...)
    .Append(context.BinaryClassification.Trainers.SdcaLogisticRegression());
var model = pipeline.Fit(trainData);
```

## Strategy 6: Excel via Xlwings

Xlwings allows writing Python UDFs for Excel:

```python
@xw.func
def analyze_text(text):
    score = model.predict_proba([text])[0][1]
    return score
```

Called in Excel as `=analyze_text(A1)`. Required: `xlwings addin install`, VBA trust settings, and `.xlsm` workbook.

## Summary Comparison

| Method | Latency | Language Support | Dependencies | Best For |
|--------|---------|-----------------|--------------|----------|
| Pickle | Negligible | Python only | Python runtime | Python-to-Python |
| Flask API | ~2s per call | Any (HTTP) | Python server + packages | Polyglot teams, prototypes |
| Docker + Flask | ~2s + network | Any (HTTP) | Docker runtime only | Production cloud deployment |
| ONNX | ~0.001s | 8+ languages | ONNX runtime only | High-performance cross-platform |
| ML.NET | Native speed | C#/.NET | .NET runtime | .NET ecosystems |
| Xlwings | ~1-2s | Excel | Python + Xlwings | Business analysts in Excel |
