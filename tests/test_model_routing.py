"""Unit tests for the model_routing module – route definitions and structure."""

from all_about_llms.model_routing import MODEL_ROUTES, ModelRoute, list_model_routes


class TestModelRouteStructure:
    def test_all_routes_are_model_route_instances(self):
        for route in MODEL_ROUTES:
            assert isinstance(route, ModelRoute)

    def test_routes_have_required_fields(self):
        for route in MODEL_ROUTES:
            assert route.task
            assert route.primary_model
            assert route.rationale
            assert route.provider_boundary

    def test_unique_task_names(self):
        tasks = [route.task for route in MODEL_ROUTES]
        assert len(tasks) == len(set(tasks)), "Duplicate task names found"

    def test_list_model_routes_returns_tuple(self):
        result = list_model_routes()
        assert isinstance(result, tuple)
        assert result is MODEL_ROUTES

    def test_expected_tasks_present(self):
        tasks = {route.task for route in MODEL_ROUTES}
        expected = {
            "live_conversation",
            "deep_reasoning_and_planning",
            "fast_routing_and_triage",
            "vision_and_multimodal_review",
            "raster_visual_generation",
        }
        assert expected == tasks

    def test_live_conversation_has_fallback(self):
        route = next(r for r in MODEL_ROUTES if r.task == "live_conversation")
        assert route.fallback_model is not None

    def test_raster_visual_generation_no_fallback(self):
        route = next(r for r in MODEL_ROUTES if r.task == "raster_visual_generation")
        assert route.fallback_model is None

    def test_model_route_serialization(self):
        route = MODEL_ROUTES[0]
        data = route.model_dump()
        assert "task" in data
        assert "primary_model" in data
        assert "fallback_model" in data
        assert "rationale" in data
        assert "provider_boundary" in data

    def test_openrouter_boundary_in_reasoning_route(self):
        route = next(r for r in MODEL_ROUTES if r.task == "deep_reasoning_and_planning")
        assert "OpenRouter" in route.provider_boundary
