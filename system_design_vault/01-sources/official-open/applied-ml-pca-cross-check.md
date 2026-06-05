---
type: official-cross-check
status: canon_ready
source_id: local_books.applied_ml_and_ai_for_engineers.chapter_6_principal_component_analysis
chapter: "6 - Principal Component Analysis"
project: agent-studio-system-design
official_sources:
  - https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html
  - https://scikit-learn.org/stable/modules/decomposition.html#pca
  - https://scikit-learn.org/stable/auto_examples/applications/plot_face_recognition.html
---

# Applied ML Ch6 PCA — Official Scikit-Learn Cross-Check

Corroboration of the Applied ML Ch6 (Principal Component Analysis) chapter note against the official Scikit-Learn PCA documentation.

## Key Corroboration Points

### API Surface Match
The Scikit-Learn `PCA` class exposes all parameters and methods described in the chapter: `n_components` (int, float, or `'mle'`), `copy`, `whiten`, `svd_solver`, `tol`, `iterated_power`, `random_state`. The chapter's code examples (`PCA(n_components=5).fit_transform(X)`, `PCA(0.8)` for variance-targeted reduction, `inverse_transform`) are all correct and reflect production API behavior.

### SVD Solver Selection (Not in the Chapter)
The chapter covers covariance-matrix eigen-decomposition as the mechanism, but Scikit's `PCA` defaults to `svd_solver='auto'` which selects the solver based on input dimensions:
- **Full SVD**: when n_samples or n_features is < 500
- **Randomized SVD** (Halko 2011): when both dims > 500 and n_components < 80% of min(n_samples, n_features)
- **ARPACK**: when n_components < min(n_samples, n_features) and `svd_solver='arpack'` is explicitly set

This matters for Agent Studio: on large sparse feature sets (e.g., text TF-IDF with 100K+ columns), `svd_solver='auto'` may silently select randomized SVD, which produces non-deterministic components between runs unless `random_state` is fixed.

### Whitening Parameter
`PCA(whiten=True)` divides components by their singular values, normalizing component variance to 1. This is not covered in the book chapter. Useful for downstream models sensitive to input scale but permanently loses the interpretability of explained_variance_ratio_ (all components show equal variance after whitening).

### Explained Variance as Float
The book covers `PCA(0.95)` for variance-targeted reduction. The Scikit docs confirm: when `n_components` is a float in (0, 1], it selects the minimum number of components such that the cumulative `explained_variance_ratio_` exceeds the given value.

### ML Pipeline Integration
Scikit's `Pipeline([('scaler', StandardScaler()), ('pca', PCA()), ('clf', LogisticRegression())])` is the canonical pattern, matching the book's recommendation to pipe standardization before PCA to avoid data leakage.

## Gaps Not Covered in the Chapter

| Gap | Impact |
|-----|--------|
| SVD solver selection (auto/randomized/full) | Non-deterministic components on large datasets without fixed random_state |
| Whitening parameter | Changes explained_variance_ratio_ semantics — all components show equal variance |
| `copy=True` default | In-place transforms may fail if input is not writeable (e.g., read-only arrays) |
| `mean_` is not automatically scaled | If StandardScaler is used before PCA, the `mean_` attribute reflects scaled input means, not original feature means |
| PCA on sparse matrices | Scikit PCA requires dense input; use `TruncatedSVD` (also called LSA) for sparse matrices — fundamentally different transform that centers differently |

## Release-Gate Implications

1. **Random state pinning**: For production pipelines using PCA on datasets > 500 samples × 500 features, pin `random_state` to ensure deterministic component output.
2. **Sparse data path**: When features are sparse (text, categorical interactions), detect and switch to `TruncatedSVD` instead of `PCA`.
3. **Whitening caveat**: Do not use `whiten=True` when `explained_variance_ratio_` is used as a downstream signal (monitoring drift, reporting).
4. **Pipeline persistence**: Save the entire `StandardScaler → PCA` pipeline as a single artifact to prevent train/serve skew from different PCA mean_ initialization.

## References

- [Scikit-Learn PCA API](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
- [Scikit-Learn Decomposition User Guide](https://scikit-learn.org/stable/modules/decomposition.html#pca)
- [Faces Recognition Example](https://scikit-learn.org/stable/auto_examples/applications/plot_face_recognition.html) — demonstrates PCA with eigenfaces and explained_variance_ratio_ visualization