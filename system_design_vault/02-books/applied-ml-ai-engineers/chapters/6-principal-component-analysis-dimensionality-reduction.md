# Chapter 6: Principal Component Analysis — Dimensionality Reduction

**type:** chapter-note  
**status:** deep_read_pass_1  
**source_id:** local_books.applied_ml_ai_engineers  
**chapter:** "6"  
**chapter_title:** "Principal Component Analysis"  
**extraction_method:** pdftotext_direct_read  
**local_source:** "/Users/saumyamehta/DS interview prep/books/Applied-Machine-Learning-and-AI-for-Engineers.pdf"  
**related:** parent note

---

## The Core Idea

PCA collapses a high-dimensional dataset into fewer dimensions while retaining most of the statistical variance. The book opens with an arresting claim: you can take 1,000 columns, reduce to 100, and keep 90%+ of the information. The mechanism is a coordinate-system rotation — the original axes are replaced with principal components: new orthogonal vectors ordered so that PC1 captures the maximum possible variance, PC2 captures the next most (under the orthogonality constraint), and so on.

Under the hood: build a covariance matrix of the features → perform eigen-decomposition → eigenvectors are the principal component directions, eigenvalues are the variance explained by each direction. Scikit's `PCA` class wraps all of this.

```python
pca = PCA(n_components=5)
X_reduced = pca.fit_transform(X)
X_restored = pca.inverse_transform(X_reduced)  # lossy
```

## The Explained Variance Ratio

After fitting, `pca.explained_variance_ratio_` gives the fraction of total dataset variance captured by each component. The values are sorted descending by definition: PC1 always explains more than PC2, PC2 more than PC3, etc.

In the LFW faces demo (2,914 pixels per image → 150 components), the sum of explained variance ratios was 0.948 — meaning ~95% of the information survived a ~95% dimensional reduction. The first component alone captured 18% of the variance; the second captured 15%. By the 150th component, each contributed less than 0.05%. The discarded 2,764 components collectively contained so little signal that faces remained recognizable after inverse transform.

**Selecting n_components:** Use a scree plot (`plt.plot(pca.explained_variance_ratio_)`) or a cumulative variance curve (`np.cumsum`). The elbow in the scree plot suggests a natural cutoff. Alternatively, pass a float to `PCA(0.8)` to auto-select the minimum number of components that retain 80% of the variance.

## Standardization Requirement

PCA is scale-sensitive. Features with larger numerical ranges dominate the covariance matrix and will be over-represented in the principal components. Always apply `StandardScaler` (zero mean, unit variance) before PCA unless all features are already on the same physical scale. The book demonstrates this in the anonymization section with the breast cancer dataset.

## PCA vs. Feature Selection

This is a key distinction that often trips up practitioners:

| | Feature Selection | PCA |
|---|---|---|
| What happens | Columns are dropped entirely | Columns are replaced by linear combinations |
| Interpretability | Original column names survive | Components have no semantic meaning |
| Data type | Works with any features | Requires numeric, continuous features |
| Supervised? | Can use target variable (e.g., mutual information) | Unsupervised — ignores the target |

PCA is **not** feature selection. It is feature extraction. You cannot look at PC1 and say "this represents temperature" — it is a weighted sum of all original features. Use feature selection (or L1 regularization) when interpretability matters; use PCA when you need maximum compression with minimal variance loss.

## Dimensionality Reduction Decision Tree

```mermaid
flowchart TD
    A[High-dim data<br>d features, n samples] --> B{Goal?}
    B --> C[Reduce dimensions<br>for model training]
    B --> D[Visualize in 2D/3D]
    B --> E[Anonymize sensitive data]
    B --> F[Filter noise from sensors]

    C --> G{n << d?}
    G -->|Yes| H[Try PCA first<br>fast, linear, deterministic]
    G -->|No| I[Feature selection<br>or L1 regularization]

    D --> J{n_components = 2 or 3}
    J --> K[PCA — fast preview<br>keeps dissimilar points apart]
    J --> L[t-SNE — sharper clusters<br>nonlinear, compute-heavy]

    E --> M[PCA(n_components=d)<br>+ StandardScaler<br>zero information loss]

    F --> N[PCA fit on normal data<br>transform + invert<br>threshold on MSE]

    H --> O{Linear enough?}
    O -->|Yes| P[Use PCA]
    O -->|No| Q[Kernel PCA<br>or Autoencoder]
```

## PCA for Visualization

Reducing to 2 or 3 dimensions is one of PCA's most practical uses. The book walks through the handwritten digits dataset (64 dimensions → 2) and shows that classes form discernible clusters — 0s and 1s separate cleanly, 4s and 6s overlap. A 3D version (64 → 3) reveals more separation between problematic pairs. This gives a quick, visual "sanity check" before committing to a classifier.

**t-SNE contrast:** t-SNE uses a nonlinear transform that keeps similar points close together (PCA keeps dissimilar points far apart). t-SNE produces tighter clusters for visualization but is compute-intensive. Common strategy: PCA-reduce first, then run t-SNE on the PCA output.

## PCA Assumptions and Limitations

**Assumptions that matter in practice:**
- **Linearity.** PCA finds linear combinations only. If the true structure is nonlinear (e.g., a curved manifold in feature space), PCA will overestimate the number of components needed.
- **Normality (weak).** PCA assumes features follow a multivariate Gaussian _if_ you want MLE-interpretation of the covariance structure. In practice PCA works on non-Gaussian data but the explained variance ratios lose their clean statistical interpretation.
- **Large variance ≈ important signal.** This is the fundamental wager. PCA assumes the directions of greatest spread are the directions of greatest signal. That is not always true — a component with tiny variance could be the one that separates your classes (e.g., a rare but diagnostic biomarker).

**Limitations:**
- **Interpretability loss.** Each principal component is a dense linear combination of every original feature. You cannot audit "why" a component has a certain value.
- **No use of the target variable.** PCA is unsupervised — it may discard components that are useless for reconstruction but critical for classification.
- **Sensitive to outliers.** A few extreme samples can rotate the principal components dramatically (robust PCA variants exist but are not covered in this chapter).

## Agent Studio / ML Pipeline Implications

In automated feature engineering pipelines (e.g., Agent Studio-style flows):

1. **Gate PCA behind a cardinality check.** If feature count > 2x sample count, PCA is a strong candidate. Below that, feature selection is usually safer.

2. **Pipe standardization before PCA.** Build a `StandardScaler → PCA` pipeline in Scikit to avoid data leakage across train/test splits.

3. **Persist the PCA object.** The `components_` matrix and `mean_` vector must be saved alongside the model so inference transforms are consistent. Treat PCA as part of the model artifact, not a pre-processing script.

4. **Monitor explained variance drift.** If the cumulative variance of the top-k components drops significantly on production data, retrain the PCA transform — the input distribution has likely shifted.

5. **Threshold for anomaly detection is a business parameter.** In the credit card fraud example, loss=200 caught 50% of fraud with 0.03% false-positive rate. Lower thresholds catch more fraud but anger more customers. Build a configurable threshold into the pipeline, tuned via a precision-recall tradeoff curve on holdout data.

6. **Prefer PCA over t-SNE/UMAP inside the training pipeline.** t-SNE is non-deterministic and expensive; PCA is fast, deterministic, and invertible. Reserve t-SNE for one-off exploratory visualization.

## Summary of Practical Recipes from the Chapter

| Use Case | Recipe | Key Param |
|---|---|---|
| General dim reduction | `PCA(n_components=k).fit_transform(X)` | Scree plot elbow |
| Variance-targeted reduction | `PCA(0.95)` | Float in [0,1] |
| Noise filtering | PCA → inverse on noisy data | n_components capturing ~80% variance |
| Anonymization | `PCA(n_components=d)` + `StandardScaler` | n_components = original dim count |
| Visualization | `PCA(n_components=2 or 3)` | 2 or 3 |
| Anomaly detection | Fit PCA on normal data, measure reconstruction MSE | Threshold tuned on business cost |