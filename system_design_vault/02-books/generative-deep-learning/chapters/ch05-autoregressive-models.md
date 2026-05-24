# Chapter 5: Autoregressive Models

## LSTM Cell: Three Gates + Cell State

The LSTM (Long Short-Term Memory) cell introduces a **cell state** that flows through time, regulated by three gates. The full update involves 6 steps:

1. **Forget gate:** f_t = sigma(W_f · [h_{t-1}, x_t] + b_f) — decides what to discard from the cell state
2. **Input gate (part 1):** i_t = sigma(W_i · [h_{t-1}, x_t] + b_i) — decides which values to update
3. **Candidate cell state:** C_tilde = tanh(W_C · [h_{t-1}, x_t] + b_C) — new candidate values
4. **Cell state update:** C_t = f_t * C_{t-1} + i_t * C_tilde — forgetting old info + adding new info
5. **Output gate:** o_t = sigma(W_o · [h_{t-1}, x_t] + b_o) — decides what to output
6. **Hidden state:** h_t = o_t * tanh(C_t) — the filtered output

## Hidden State ≠ Cell State

This is a critical distinction:

- **Cell state (C_t):** The long-term memory — flows through the cell with minimal modification (only forgetting and adding)
- **Hidden state (h_t):** The working memory — output, filtered from cell state, fed to the next time step

The gating mechanism allows the LSTM to learn **long-range dependencies** — information can be stored in the cell state for hundreds of time steps without degradation (unlike vanilla RNNs where gradients vanish).

## Temperature Scaling for Sampling

When generating from an autoregressive model, **temperature** controls the sampling distribution:

```
p_i = exp(logits_i / T) / sum_j(exp(logits_j / T))
```

- **Low temperature (T → 0):** Deterministic — always picks the highest probability token
- **High temperature (T → inf):** Exploratory — uniform distribution over all tokens

Typical ranges:
- T = 0.5-0.8: Creative but coherent
- T = 1.0: Standard sampling
- T > 1.5: Very random, may degrade quality

## Stacked LSTMs

Stacking multiple LSTM layers creates **hierarchical feature learning**:

- Lower layers capture local, short-range patterns (word-level syntax)
- Higher layers capture global, long-range patterns (sentence-level semantics)

```python
model.add(LSTM(128, return_sequences=True))  # Returns sequences for stacking
model.add(LSTM(64))                           # Only returns final hidden state
```

The first layer returns sequences so the second layer receives a sequence of hidden states.

## GRU: Simplified Alternative

The Gated Recurrent Unit (GRU) is a simplified LSTM with **2 gates** (not 3) and **no separate cell state**:

1. **Update gate:** Combines forget and input gates into one — decides how much of the past to keep
2. **Reset gate:** Decides how much of the past to forget when computing the new candidate

GRU has fewer parameters than LSTM, trains faster, and often performs comparably. It's preferred when computational resources are limited.

```mermaid
graph TD
    subgraph "LSTM Cell Internals"
        X[X_t<br/>Input] --> H_prev[H_{t-1}]
        H_prev --> F[Forget Gate<br/>σ]
        H_prev --> I[Input Gate<br/>σ]
        H_prev --> O[Output Gate<br/>σ]
        H_prev --> C_Cand[Candidate<br/>tanh]

        C_prev[C_{t-1}] --> F
        F -->|f_t| M1[Multiply]
        C_prev --> M1

        I -->|i_t| M2[Multiply]
        C_Cand --> M2

        M1 --> Add[Add → C_t]
        M2 --> Add

        Add -->|C_t| M3[Multiply]
        O -->|o_t| M3
        M3 -->|tanh| H_t[H_t<br/>Hidden State]
    end

    style X fill:#e74c3c,color:#fff
    style C_prev fill:#3498db,color:#fff
    style H_t fill:#2ecc71,color:#fff
    style Add fill:#f39c12,color:#fff
```