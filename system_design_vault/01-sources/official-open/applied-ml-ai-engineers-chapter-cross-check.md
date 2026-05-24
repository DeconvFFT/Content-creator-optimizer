# Applied ML AI Engineers — Chapter Cross-Check
## Canonical docs corroboration for deep_read_pass_1 → canon_ready

| Chapter | Source URL | Key Corroboration |
|---------|-----------|-------------------|
| **Ch3 (Classification)** | https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsClassifier.html | n_neighbors, weights, algorithm='auto', metric='minkowski', predict_proba available |
| | https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html | penalty='l2', C=1.0, solver='lbfgs', multi_class='auto', predict vs predict_proba |
| | https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.MultinomialNB.html | alpha=1.0, fit_prior=True, class_prior, partial_fit for incremental learning |
| **Ch6 (PCA)** | https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html | n_components, svd_solver='auto', explained_variance_ratio_ as array per component |
| | (same URL) explained_variance_ratio_ | Sum of ratios indicates retained variance; sorted descending; components_ for eigenvectors |
| **Ch7 (Operationalizing)** | https://onnx.ai/ + https://onnxruntime.ai/ | ONNX standard for model interchange; onnxruntime for cross-platform inference; sklearn-onnx converter |
| | https://mlflow.org/docs/latest/deployment/index.html | mlflow models serve --port; REST API (POST /invocations); pyfunc flavor; deploy to SageMaker/Azure |
| | https://mlflow.org/docs/latest/models.html | MLmodel format, conda.yaml/pyfunc predict(), model registry stages |

## Notes for canon_ready validation

- **Ch3**: Confirm book uses `n_neighbors` (not `k`), `penalty`/`C` naming, and `alpha` smoothing correctly per official sklearn API. Check multiclass handling matches sklearn default behavior.
- **Ch6**: Verify explained_variance_ratio_ usage matches sklearn output shape (n_components,). Check SVD solver discussion aligns with sklearn's svd_solver param.
- **Ch7**: Ensure ONNX conversion flow (sklearn→onnx→onnxruntime) matches official tutorials. Verify MLflow serve command syntax and endpoint expectations.

## Source freshness
All URLs above from scikit-learn 1.5.x, ONNX 1.16, MLflow 2.x doc tree — stable and canonical.