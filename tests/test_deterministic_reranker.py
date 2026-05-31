"""Unit tests for the DeterministicRerankerProvider – scoring and ranking logic."""

import asyncio


from all_about_llms.providers.interfaces import RerankCandidate, RerankRequest
from all_about_llms.providers.rerank import (
    DeterministicRerankerProvider,
    _reason,
    _score_candidate,
)


# ─── _score_candidate ────────────────────────────────────────────────────────


class TestScoreCandidate:
    def _make_candidate(self, quality="needs_review", freshness="unknown", **kwargs):
        metadata = {"quality_status": quality, "freshness_status": freshness, **kwargs}
        return RerankCandidate(
            candidate_id="c1",
            title="Test",
            rank=1,
            metadata=metadata,
        )

    def test_strong_quality_base_score(self):
        candidate = self._make_candidate(quality="strong", freshness="current")
        score = _score_candidate(candidate)
        assert score > 0.85

    def test_weak_quality_low_score(self):
        candidate = self._make_candidate(quality="weak", freshness="stale")
        score = _score_candidate(candidate)
        assert score < 0.15

    def test_acceptable_quality_mid_score(self):
        candidate = self._make_candidate(quality="acceptable", freshness="evergreen")
        score = _score_candidate(candidate)
        assert 0.6 < score < 0.85

    def test_freshness_current_adds_score(self):
        base = self._make_candidate(quality="acceptable", freshness="unknown")
        current = self._make_candidate(quality="acceptable", freshness="current")
        assert _score_candidate(current) > _score_candidate(base)

    def test_freshness_stale_reduces_score(self):
        base = self._make_candidate(quality="acceptable", freshness="unknown")
        stale = self._make_candidate(quality="acceptable", freshness="stale")
        assert _score_candidate(stale) < _score_candidate(base)

    def test_snippet_adds_score(self):
        without_snippet = RerankCandidate(
            candidate_id="c1",
            title="Test",
            rank=1,
            metadata={"quality_status": "acceptable", "freshness_status": "current"},
        )
        with_snippet = RerankCandidate(
            candidate_id="c2",
            title="Test",
            snippet="A relevant snippet",
            rank=1,
            metadata={"quality_status": "acceptable", "freshness_status": "current"},
        )
        assert _score_candidate(with_snippet) > _score_candidate(without_snippet)

    def test_published_at_adds_score(self):
        without = self._make_candidate(quality="acceptable", freshness="current")
        with_pub = self._make_candidate(
            quality="acceptable", freshness="current", has_published_at=True
        )
        assert _score_candidate(with_pub) > _score_candidate(without)

    def test_higher_search_rank_reduces_score(self):
        rank1 = RerankCandidate(
            candidate_id="c1",
            title="Test",
            rank=1,
            metadata={"quality_status": "acceptable", "freshness_status": "current", "search_rank": 1},
        )
        rank10 = RerankCandidate(
            candidate_id="c2",
            title="Test",
            rank=10,
            metadata={"quality_status": "acceptable", "freshness_status": "current", "search_rank": 10},
        )
        assert _score_candidate(rank1) > _score_candidate(rank10)

    def test_score_clamped_to_0_1(self):
        # Worst possible case
        candidate = self._make_candidate(quality="weak", freshness="stale")
        candidate.rank = 25
        candidate.metadata["search_rank"] = 25
        score = _score_candidate(candidate)
        assert 0.0 <= score <= 1.0

    def test_unknown_quality_defaults_to_needs_review(self):
        candidate = self._make_candidate(quality="nonexistent", freshness="current")
        expected = self._make_candidate(quality="needs_review", freshness="current")
        assert _score_candidate(candidate) == _score_candidate(expected)


# ─── _reason ─────────────────────────────────────────────────────────────────


class TestReason:
    def test_basic_reason_format(self):
        candidate = RerankCandidate(
            candidate_id="c1",
            title="Test",
            rank=1,
            metadata={"quality_status": "strong", "freshness_status": "current"},
        )
        reason = _reason(candidate, 0.9)
        assert "quality=strong" in reason
        assert "freshness=current" in reason

    def test_snippet_mentioned(self):
        candidate = RerankCandidate(
            candidate_id="c1",
            title="Test",
            snippet="Some text",
            rank=1,
            metadata={"quality_status": "strong", "freshness_status": "current"},
        )
        reason = _reason(candidate, 0.9)
        assert "snippet" in reason

    def test_published_at_mentioned(self):
        candidate = RerankCandidate(
            candidate_id="c1",
            title="Test",
            rank=1,
            metadata={
                "quality_status": "strong",
                "freshness_status": "current",
                "has_published_at": True,
            },
        )
        reason = _reason(candidate, 0.9)
        assert "published_at" in reason

    def test_low_score_mentioned(self):
        candidate = RerankCandidate(
            candidate_id="c1",
            title="Test",
            rank=1,
            metadata={"quality_status": "weak", "freshness_status": "stale"},
        )
        reason = _reason(candidate, 0.1)
        assert "low_score" in reason


# ─── DeterministicRerankerProvider ───────────────────────────────────────────


class TestDeterministicRerankerProvider:
    def setup_method(self):
        self.provider = DeterministicRerankerProvider()

    def test_provider_id(self):
        assert self.provider.provider_id == "deterministic_source_quality_v1"

    def test_rerank_returns_sorted_by_score(self):
        candidates = [
            RerankCandidate(
                candidate_id="weak_one",
                title="Weak",
                rank=1,
                metadata={"quality_status": "weak", "freshness_status": "stale"},
            ),
            RerankCandidate(
                candidate_id="strong_one",
                title="Strong",
                rank=2,
                metadata={"quality_status": "strong", "freshness_status": "current"},
            ),
        ]
        request = RerankRequest(query="test query", candidates=candidates)
        results = asyncio.run(self.provider.rerank(request))

        assert results[0].candidate_id == "strong_one"
        assert results[0].rank_after == 1
        assert results[1].candidate_id == "weak_one"
        assert results[1].rank_after == 2

    def test_rerank_respects_top_k(self):
        candidates = [
            RerankCandidate(
                candidate_id=f"c{i}",
                title=f"Candidate {i}",
                rank=i,
                metadata={"quality_status": "acceptable", "freshness_status": "current"},
            )
            for i in range(5)
        ]
        request = RerankRequest(query="test", candidates=candidates, top_k=2)
        results = asyncio.run(self.provider.rerank(request))
        assert len(results) == 2

    def test_rerank_preserves_rank_before(self):
        candidates = [
            RerankCandidate(
                candidate_id="c1",
                title="First",
                rank=5,
                metadata={"quality_status": "strong", "freshness_status": "current"},
            ),
        ]
        request = RerankRequest(query="test", candidates=candidates)
        results = asyncio.run(self.provider.rerank(request))
        assert results[0].rank_before == 5
        assert results[0].rank_after == 1

    def test_rerank_metadata_includes_provider_id(self):
        candidates = [
            RerankCandidate(
                candidate_id="c1",
                title="Test",
                rank=1,
                metadata={"quality_status": "strong", "freshness_status": "current"},
            ),
        ]
        request = RerankRequest(query="test", candidates=candidates)
        results = asyncio.run(self.provider.rerank(request))
        assert results[0].metadata["provider_id"] == "deterministic_source_quality_v1"

    def test_rerank_empty_candidates(self):
        request = RerankRequest(query="test", candidates=[])
        results = asyncio.run(self.provider.rerank(request))
        assert results == []

    def test_stable_sort_on_tie(self):
        """When scores are equal, original rank and candidate_id break ties."""
        candidates = [
            RerankCandidate(
                candidate_id="b",
                title="B",
                rank=2,
                metadata={"quality_status": "acceptable", "freshness_status": "current"},
            ),
            RerankCandidate(
                candidate_id="a",
                title="A",
                rank=1,
                metadata={"quality_status": "acceptable", "freshness_status": "current"},
            ),
        ]
        request = RerankRequest(query="test", candidates=candidates)
        results = asyncio.run(self.provider.rerank(request))
        # Same quality/freshness, rank 1 < rank 2 so "a" should come first
        assert results[0].candidate_id == "a"
        assert results[1].candidate_id == "b"
