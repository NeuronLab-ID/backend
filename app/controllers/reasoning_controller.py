# Reasoning Controller
# Handles reasoning generation and streaming for quest steps

import json
import asyncio
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.models.db import QuestReasoning
from app.repositories import QuestRepository
from app.services.reasoning_service import ReasoningService


class ReasoningController:
    """Controller for reasoning generation and streaming."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = QuestRepository(db)

    def get_cached_reasoning(self, problem_id: int) -> dict:
        """Get cached full reasoning for a problem."""
        reasoning = self.repository.get_reasoning(problem_id)

        if reasoning:
            return {
                "exists": True,
                "data": json.loads(reasoning.reasoning_data),
                "created_at": reasoning.created_at.isoformat(),
            }
        return {"exists": False, "data": None}

    async def stream_full_reasoning(
        self,
        problem_id: int,
        user_id: int,
        force: bool = False,
        use_perplexity: bool = False,
        use_perplexity_reasoning: bool = False,
    ) -> StreamingResponse:
        """Generate and stream full reasoning for all quest steps."""
        # Check for cached reasoning
        existing = self.repository.get_reasoning(problem_id)

        if force and existing:
            self.repository.delete_reasoning(problem_id)
            existing = None

        if existing:
            return self._stream_cached_reasoning(existing)

        # Get quest data
        quest = self.repository.get_by_problem_id(problem_id)
        if not quest:
            raise HTTPException(404, "Quest not found")

        quest_data = json.loads(quest.data)
        sub_quests = quest_data.get("sub_quests", [])

        if not sub_quests:
            raise HTTPException(400, "No quest steps found")

        return StreamingResponse(
            self._generate_reasoning_stream(
                problem_id,
                user_id,
                quest_data,
                sub_quests,
                use_perplexity,
                use_perplexity_reasoning,
            ),
            media_type="text/event-stream",
        )

    def _stream_cached_reasoning(self, reasoning: QuestReasoning) -> StreamingResponse:
        """Stream cached reasoning data."""
        cached_data = json.loads(reasoning.reasoning_data)

        async def stream_cached():
            if cached_data.get("web_references"):
                yield f"data: {json.dumps({'type': 'search_result', 'data': {'content': cached_data['web_references']}})}\n\n"
                yield f"data: {json.dumps({'type': 'search_complete', 'data': {'chars': len(cached_data['web_references'])}})}\n\n"

            for step_data in cached_data.get("steps", []):
                yield f"data: {json.dumps({'type': 'step', 'data': step_data})}\n\n"
                await asyncio.sleep(0.1)

            if cached_data.get("summary"):
                yield f"data: {json.dumps({'type': 'summary', 'data': cached_data['summary']})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'cached': True})}\n\n"

        return StreamingResponse(stream_cached(), media_type="text/event-stream")

    async def _generate_reasoning_stream(
        self,
        problem_id: int,
        user_id: int,
        quest_data: dict,
        sub_quests: list,
        use_perplexity: bool,
        use_perplexity_reasoning: bool,
    ):
        """Generate reasoning stream."""
        try:
            service = ReasoningService(
                use_perplexity=use_perplexity,
                use_perplexity_reasoning=use_perplexity_reasoning,
            )

            complete_data = None

            async for event in service.stream_full_reasoning(quest_data, sub_quests):
                if event.get("type") == "complete":
                    complete_data = event["data"]
                    continue

                yield f"data: {json.dumps(event)}\n\n"

            # Save to database
            if complete_data:
                # NOTE: Intentional SessionLocal() - the request-scoped DB session closes before
                # this async generator finishes yielding SSE events. This separate session handles
                # the DB write after streaming completes.
                from app.database import SessionLocal

                db = SessionLocal()
                try:
                    new_reasoning = QuestReasoning(
                        problem_id=problem_id,
                        reasoning_data=json.dumps(complete_data),
                        created_by=user_id,
                    )
                    db.add(new_reasoning)
                    db.commit()
                finally:
                    db.close()

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
