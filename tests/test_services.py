# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportOptionalSubscript=false, reportAny=false, reportPrivateUsage=false
"""
Tests for service modules: solution_generator, math_sample_service,
export_service, quest_service, and json_utils.
All AI providers are mocked — no real API keys needed.
"""

import asyncio
import importlib
import json
from unittest.mock import patch, MagicMock, AsyncMock, mock_open


class TestSolutionGenerator:
    def test_generate_solution_success(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(return_value="def solution():\n    return 1")
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.solution_generator as solution_generator

            importlib.reload(solution_generator)
            result = asyncio.get_event_loop().run_until_complete(
                solution_generator.generate_solution({"title": "Test"})
            )
        assert result == "def solution():\n    return 1"

    def test_generate_solution_strips_python_block(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(return_value="```python\nprint('hi')\n```")
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.solution_generator as solution_generator

            importlib.reload(solution_generator)
            result = asyncio.get_event_loop().run_until_complete(
                solution_generator.generate_solution({"title": "Test"})
            )
        assert result == "print('hi')"

    def test_generate_solution_returns_none_on_empty(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(return_value=None)
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.solution_generator as solution_generator

            importlib.reload(solution_generator)
            result = asyncio.get_event_loop().run_until_complete(
                solution_generator.generate_solution({"title": "Test"})
            )
        assert result is None

    def test_generate_solution_handles_exception(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(side_effect=Exception("boom"))
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.solution_generator as solution_generator

            importlib.reload(solution_generator)
            result = asyncio.get_event_loop().run_until_complete(
                solution_generator.generate_solution({"title": "Test"})
            )
        assert result is None


class TestMathSampleService:
    def test_generate_sample_success(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(return_value='{"steps": ["Step 1"], "result": "$x=1$"}')
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.math_sample_service as math_sample_service

            importlib.reload(math_sample_service)
            service = math_sample_service.MathSampleService()
            result = asyncio.get_event_loop().run_until_complete(service.generate_sample("Quadratic", "x^2", "easy"))
        assert result["success"] is True
        assert result["steps"] == ["Step 1"]
        assert result["result"] == "$x=1$"

    def test_generate_sample_retries_and_succeeds(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(
            side_effect=["not json", '{"steps": ["Step 1"], "result": "$x=1$"}']
        )
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.math_sample_service as math_sample_service

            importlib.reload(math_sample_service)
            service = math_sample_service.MathSampleService()
            result = asyncio.get_event_loop().run_until_complete(service.generate_sample("Quadratic", "x^2", "easy"))
        assert result["success"] is True
        assert mock_provider.generate_reasoning.call_count == 2

    def test_generate_sample_retry_failure(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(return_value="garbage")
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.math_sample_service as math_sample_service

            importlib.reload(math_sample_service)
            service = math_sample_service.MathSampleService()
            result = asyncio.get_event_loop().run_until_complete(service.generate_sample("Quadratic", "x^2", "easy"))
        assert result["success"] is False
        assert result["steps"] == []
        assert "Failed to parse" in result["error"]

    def test_generate_sample_exception(self):
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(side_effect=Exception("boom"))
        with patch("app.services.ai_providers.get_provider") as mock_get:
            mock_get.return_value = mock_provider
            import app.services.math_sample_service as math_sample_service

            importlib.reload(math_sample_service)
            service = math_sample_service.MathSampleService()
            result = asyncio.get_event_loop().run_until_complete(service.generate_sample("Quadratic", "x^2", "easy"))
        assert result["success"] is False
        assert result["error"] == "boom"


class TestExportService:
    def test_convert_latex_delimiters_parens(self):
        from app.services.export_service import convert_latex_delimiters

        assert convert_latex_delimiters("Value is \\(x\\)") == "Value is $x$"

    def test_convert_latex_delimiters_brackets(self):
        from app.services.export_service import convert_latex_delimiters

        assert convert_latex_delimiters("Eqn: \\[x\\]") == "Eqn: $$x$$"

    def test_get_latex_preamble_contains_fields(self):
        from app.services.export_service import get_latex_preamble

        preamble = get_latex_preamble("Problem #1", "January 01, 2024")
        assert "\\documentclass" in preamble
        assert "\\title" in preamble
        assert "Problem 1" in preamble

    def test_export_to_markdown_no_ai_structure(self):
        with patch("app.services.export_service.get_search_provider") as mock_search:
            mock_provider = MagicMock()
            mock_provider.is_configured.return_value = False
            mock_search.return_value = mock_provider
            from app.services.export_service import ExportService

            service = ExportService()
            steps = [
                {"step": 1, "title": "Setup", "reasoning": "Use \\(x\\)"},
                {"step": 2, "title": "Solve", "reasoning": "Then \\[[y]\\]"},
            ]
            result = asyncio.get_event_loop().run_until_complete(
                service.export_to_markdown("Test Problem", steps, "Summary", use_ai=False)
            )
        markdown = result["markdown"]
        assert result["enhanced"] is False
        assert "# Test Problem - Solution Reasoning" in markdown
        assert "## Step 1: Setup" in markdown
        assert "$x$" in markdown
        assert "$$[y]$$" in markdown
        assert "## Summary" in markdown

    def test_export_to_markdown_with_references(self):
        with patch("app.services.export_service.get_search_provider") as mock_search:
            mock_provider = MagicMock()
            mock_provider.is_configured.return_value = False
            mock_search.return_value = mock_provider
            from app.services.export_service import ExportService

            service = ExportService()
            steps = [{"step": 1, "title": "Setup", "reasoning": "Use \\(x\\)"}]
            result = asyncio.get_event_loop().run_until_complete(
                service.export_to_markdown(
                    "Test Problem",
                    steps,
                    "Summary",
                    web_references="Ref \\(x\\)",
                    use_ai=False,
                )
            )
        markdown = result["markdown"]
        assert "## References" in markdown
        assert "Ref $x$" in markdown

    def test_clean_latex_result_strips_wrapper_and_adds_preamble(self):
        from app.services.export_service import ExportService

        service = ExportService()
        latex_result = "```latex\n\\section{Intro}\n```"
        cleaned = service._clean_latex_result(latex_result, "Problem", "January 01, 2024", "NeuronLab AI")
        assert cleaned.strip().startswith("\\documentclass")
        assert "\\section{Intro}" in cleaned
        assert "\\end{document}" in cleaned

    def test_clean_latex_result_adds_missing_end(self):
        from app.services.export_service import ExportService

        service = ExportService()
        latex_result = "\\documentclass{article}\n\\begin{document}\nText"
        cleaned = service._clean_latex_result(latex_result, "Problem", "January 01, 2024", "NeuronLab AI")
        assert "\\end{document}" in cleaned

    def test_generate_basic_latex_sections_and_escapes(self):
        from app.services.export_service import ExportService

        service = ExportService()
        steps = [
            {
                "step": 1,
                "title": "Title_1",
                "reasoning": "Use **bold** & 100% in #1",
            }
        ]
        latex = service._generate_basic_latex("Problem", "January 01, 2024", steps, "Summary with 50% &")
        assert "\\section{Step 1: Title 1}" in latex
        assert "\\textbf{bold}" in latex
        assert "\\%" in latex
        assert "\\&" in latex
        assert "\\end{document}" in latex

    def test_export_to_latex_fallback_no_ai(self):
        with patch("app.services.export_service.get_search_provider") as mock_search:
            mock_provider = MagicMock()
            mock_provider.is_configured.return_value = False
            mock_search.return_value = mock_provider
            from app.services.export_service import ExportService

            service = ExportService()
            steps = [{"step": 1, "title": "Setup", "reasoning": "Text"}]
            result = asyncio.get_event_loop().run_until_complete(service.export_to_latex("Test", steps, "Summary"))
        assert result["ai_generated"] is False
        assert "\\end{document}" in result["latex"]


class TestQuestService:
    def test_get_or_generate_quest_db_cache_hit(self, db_session):
        from app.models.db import Quest
        from app.services.quest_service import get_or_generate_quest

        quest_data = {"steps": ["one"]}
        db_session.add(Quest(problem_id=1, data=json.dumps(quest_data)))
        db_session.commit()

        result = asyncio.get_event_loop().run_until_complete(get_or_generate_quest(db_session, 1))
        assert result["source"] == "database"
        assert result["quest"] == quest_data

    def test_get_or_generate_quest_file_fallback(self, db_session):
        from app.models.db import Quest
        from app.services.quest_service import get_or_generate_quest

        quest_data = {"steps": ["one"]}
        file_data = json.dumps(quest_data)
        with (
            patch("app.services.quest_service.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=file_data)),
        ):
            result = asyncio.get_event_loop().run_until_complete(get_or_generate_quest(db_session, 2))
        assert result["source"] == "file"
        cached = db_session.query(Quest).filter(Quest.problem_id == 2).first()
        assert cached is not None

    def test_get_or_generate_quest_not_found(self, db_session):
        from app.services.quest_service import get_or_generate_quest

        with patch("app.services.quest_service.Path.exists", return_value=False):
            result = asyncio.get_event_loop().run_until_complete(get_or_generate_quest(db_session, 999))
        assert result is None

    def test_get_quest_status_db_found(self, db_session):
        from app.models.db import Quest
        from app.services.quest_service import get_quest_status

        db_session.add(Quest(problem_id=1, data=json.dumps({"steps": []})))
        db_session.commit()
        result = get_quest_status(db_session, 1)
        assert result == {"available": True, "source": "database"}

    def test_get_quest_status_file_found(self, db_session):
        from app.services.quest_service import get_quest_status

        with patch("app.services.quest_service.Path.exists", return_value=True):
            result = get_quest_status(db_session, 2)
        assert result == {"available": True, "source": "file"}

    def test_get_quest_status_problem_exists(self, db_session, sample_problem):
        from app.services.quest_service import get_quest_status

        with patch("app.services.quest_service.Path.exists", return_value=False):
            result = get_quest_status(db_session, sample_problem.id)
        assert result == {"available": False, "can_generate": True}

    def test_get_quest_status_problem_not_found(self, db_session):
        from app.services.quest_service import get_quest_status

        with patch("app.services.quest_service.Path.exists", return_value=False):
            result = get_quest_status(db_session, 999)
        assert result["available"] is False
        assert result["can_generate"] is False
        assert result["error"] == "Problem not found"


class TestJsonUtils:
    def test_try_parse_json_valid(self):
        from app.utils.json_utils import try_parse_json

        text = '{"steps": ["Step 1"], "result": "$x=1$"}'
        assert try_parse_json(text) == {"steps": ["Step 1"], "result": "$x=1$"}

    def test_try_parse_json_markdown_wrapper(self):
        from app.utils.json_utils import try_parse_json

        text = '```json\n{"steps": ["Step 1"], "result": "$x=1$"}\n```'
        assert try_parse_json(text) == {"steps": ["Step 1"], "result": "$x=1$"}

    def test_try_parse_json_unescaped_latex(self):
        from app.utils.json_utils import try_parse_json

        text = '{"steps": ["Use \\alpha"], "result": "$x=1$"}'
        assert try_parse_json(text) == {
            "steps": ["Use \\alpha"],
            "result": "$x=1$",
        }

    def test_try_parse_json_invalid_returns_none(self):
        from app.utils.json_utils import try_parse_json

        assert try_parse_json("not json") is None

    def test_clean_ai_response_removes_wrapper(self):
        from app.utils.json_utils import clean_ai_response

        text = '```json\n{"a": 1}\n```'
        assert clean_ai_response(text) == '{"a": 1}'

    def test_clean_ai_response_passthrough(self):
        from app.utils.json_utils import clean_ai_response

        assert clean_ai_response("plain text") == "plain text"
