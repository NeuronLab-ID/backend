"""
Quest routes for CRUD and execution.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import json
import asyncio

from app.config import LOCAL_DEV
from app.database import SessionLocal
from app.routes.auth import get_current_user
from app.models.db import Quest, QuestProgress, QuestReasoning
from app.models.schemas import QuestExecuteRequest, QuestCreateRequest, QuestProgressSaveRequest, QuestReasoningRequest
from app.services.executor import execute_code
from app.services import get_provider, get_search_provider, get_reasoning_provider
from app.services.hint_generator import AI_BACKEND  # For backward compatibility


router = APIRouter()


@router.get("/quests/{problem_id}")
async def get_quest(problem_id: int, generate: bool = False, user_id: int = Depends(get_current_user)):
    """
    Get quest for a problem (requires auth).
    
    Args:
        problem_id: Problem ID
        generate: If True and quest not found, generate on-demand (slow, ~60s)
    """
    from app.services.quest_service import get_or_generate_quest, generate_quest_on_demand
    
    db = SessionLocal()
    try:
        # Try to get from database or file
        result = await get_or_generate_quest(db, problem_id)
        
        if result:
            return result
        
        # Quest not available
        if generate:
            # Try on-demand generation (blocking, slow)
            result = await generate_quest_on_demand(db, problem_id)
            if result:
                return result
            raise HTTPException(500, "Quest generation failed")
        
        raise HTTPException(404, "Quest not found for this problem. Use ?generate=true to generate on-demand.")
    finally:
        db.close()


@router.post("/quest/execute")
async def execute_quest_code(request: QuestExecuteRequest, user_id: int = Depends(get_current_user)):
    """Execute code for a quest exercise (requires auth)."""
    db = SessionLocal()
    try:
        quest = db.query(Quest).filter(Quest.problem_id == request.problem_id).first()
        if not quest:
            raise HTTPException(404, "Quest not found")
        quest_data = json.loads(quest.data)
    finally:
        db.close()
    
    # Find the sub_quest for this step
    sub_quests = quest_data.get("sub_quests", [])
    sub_quest = next((sq for sq in sub_quests if sq.get("step") == request.step), None)
    
    if not sub_quest:
        raise HTTPException(404, f"Step {request.step} not found in quest")
    
    # Get exercise test cases
    exercise = sub_quest.get("exercise", {})
    test_cases = exercise.get("test_cases", [])
    
    if not test_cases:
        raise HTTPException(400, "No test cases found for this exercise")
    
    # Execute code
    result = await execute_code(
        code=request.code,
        test_cases=test_cases
    )
    
    return result


@router.post("/quests/create")
async def create_quest(request: QuestCreateRequest, user=Depends(get_current_user)):
    """Create a quest (LOCAL_DEV only)."""
    if not LOCAL_DEV:
        raise HTTPException(403, "Quest creation is only allowed in local development mode")
    
    db = SessionLocal()
    try:
        # Check if quest already exists
        existing = db.query(Quest).filter(Quest.problem_id == request.problem_id).first()
        if existing:
            raise HTTPException(400, "Quest already exists for this problem")
        
        quest = Quest(
            problem_id=request.problem_id,
            data=json.dumps(request.data),
            created_by=user["user_id"] if isinstance(user, dict) else user
        )
        db.add(quest)
        db.commit()
        db.refresh(quest)
        
        return {"message": "Quest created", "id": quest.id}
    finally:
        db.close()


@router.get("/quests/check/{problem_id}")
async def check_quest_exists(problem_id: int, user_id: int = Depends(get_current_user)):
    """Check if a quest exists for a problem and whether it can be generated (requires auth)."""
    from app.services.quest_service import get_quest_status
    
    db = SessionLocal()
    try:
        status = get_quest_status(db, problem_id)
        status["local_dev"] = LOCAL_DEV
        return status
    finally:
        db.close()


@router.post("/quest/progress")
async def save_quest_progress(request: QuestProgressSaveRequest, user_id: int = Depends(get_current_user)):
    """Save progress for a quest step (mark as completed with code)."""
    db = SessionLocal()
    try:
        # Check if progress already exists
        existing = db.query(QuestProgress).filter(
            QuestProgress.user_id == user_id,
            QuestProgress.problem_id == request.problem_id,
            QuestProgress.step == request.step
        ).first()
        
        if existing:
            # Update existing progress
            existing.code = request.code
            existing.completed = True
        else:
            # Create new progress
            progress = QuestProgress(
                user_id=user_id,
                problem_id=request.problem_id,
                step=request.step,
                code=request.code,
                completed=True
            )
            db.add(progress)
        
        db.commit()
        return {"message": "Progress saved", "step": request.step}
    finally:
        db.close()


@router.get("/quest/progress/{problem_id}")
async def get_quest_progress(problem_id: int, user_id: int = Depends(get_current_user)):
    """Get user's progress for all steps of a quest."""
    db = SessionLocal()
    try:
        progress = db.query(QuestProgress).filter(
            QuestProgress.user_id == user_id,
            QuestProgress.problem_id == problem_id
        ).all()
        
        return {
            "progress": [
                {
                    "step": p.step,
                    "code": p.code,
                    "completed": p.completed,
                    "created_at": p.created_at.isoformat()
                }
                for p in progress
            ]
        }
    finally:
        db.close()


@router.post("/quest/reasoning")
async def generate_test_case_reasoning(request: QuestReasoningRequest, user_id: int = Depends(get_current_user)):
    """Generate step-by-step reasoning for a test case (Input, Process, Output)."""
    from app.services.hint_generator import create_client, AI_MODEL
    
    try:
        client = create_client()
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a programming tutor explaining how to solve a test case step by step.
Given a function signature, test input, and expected output, explain:
1. INPUT: What the input represents and its values
2. PROCESS: The step-by-step calculation/algorithm to transform input to output
3. OUTPUT: What the final result is and why

Keep each section concise (2-4 sentences max). Use mathematical notation when helpful.
Format your response EXACTLY as:
INPUT: [your explanation]
PROCESS: [your explanation]
OUTPUT: [your explanation]"""
                },
                {
                    "role": "user",
                    "content": f"""Function: {request.function_signature}
Test Input: {request.test_input}
Expected Output: {request.expected_output}

Explain the reasoning step by step:"""
                }
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        content = response.choices[0].message.content or ""
        
        # Parse the response into sections
        input_section = ""
        process_section = ""
        output_section = ""
        
        lines = content.strip().split('\n')
        current_section = None
        
        for line in lines:
            line_upper = line.upper()
            if line_upper.startswith("INPUT:"):
                current_section = "input"
                input_section = line[6:].strip()
            elif line_upper.startswith("PROCESS:"):
                current_section = "process"
                process_section = line[8:].strip()
            elif line_upper.startswith("OUTPUT:"):
                current_section = "output"
                output_section = line[7:].strip()
            elif current_section:
                if current_section == "input":
                    input_section += " " + line.strip()
                elif current_section == "process":
                    process_section += " " + line.strip()
                elif current_section == "output":
                    output_section += " " + line.strip()
        
        return {
            "input": input_section.strip() or f"Input: {request.test_input}",
            "process": process_section.strip() or "Processing the input to compute the result.",
            "output": output_section.strip() or f"Expected output: {request.expected_output}"
        }
        
    except Exception as e:
        # Return a fallback response
        return {
            "input": f"Input: {request.test_input}",
            "process": f"Error generating reasoning: {str(e)}",
            "output": f"Expected output: {request.expected_output}"
        }


@router.get("/quest/full-reasoning/{problem_id}")
async def get_full_reasoning(problem_id: int, user_id: int = Depends(get_current_user)):
    """Get cached full reasoning for a problem if it exists."""
    db = SessionLocal()
    try:
        reasoning = db.query(QuestReasoning).filter(
            QuestReasoning.problem_id == problem_id
        ).first()
        
        if reasoning:
            return {
                "exists": True,
                "data": json.loads(reasoning.reasoning_data),
                "created_at": reasoning.created_at.isoformat()
            }
        return {"exists": False, "data": None}
    finally:
        db.close()


@router.get("/quest/full-reasoning/{problem_id}/stream")
async def stream_full_reasoning(problem_id: int, force: bool = False, usePerplexity: bool = False, usePerplexityReasoning: bool = False, user_id: int = Depends(get_current_user)):
    """Generate and stream full reasoning for all quest steps using SSE.
    
    Args:
        force: If True, delete existing cached reasoning and regenerate fresh.
        usePerplexity: If True, use Perplexity API to search for web references.
        usePerplexityReasoning: If True, use Perplexity with Claude 4.5 Sonnet Thinking for reasoning generation.
    """
    db = SessionLocal()
    try:
        # Check for cached reasoning first
        existing = db.query(QuestReasoning).filter(QuestReasoning.problem_id == problem_id).first()
        
        # If force regenerate, delete existing
        if force and existing:
            db.delete(existing)
            db.commit()
            existing = None
        
        if existing:
            # Return cached data as SSE events
            cached_data = json.loads(existing.reasoning_data)
            
            async def stream_cached():
                for step_data in cached_data.get("steps", []):
                    yield f"data: {json.dumps({'type': 'step', 'data': step_data})}\n\n"
                    await asyncio.sleep(0.1)  # Small delay for UI
                
                if cached_data.get("summary"):
                    yield f"data: {json.dumps({'type': 'summary', 'data': cached_data['summary']})}\n\n"
                
                yield f"data: {json.dumps({'type': 'done', 'cached': True})}\n\n"
            
            return StreamingResponse(stream_cached(), media_type="text/event-stream")
        
        # Get quest data
        quest = db.query(Quest).filter(Quest.problem_id == problem_id).first()
        if not quest:
            raise HTTPException(404, "Quest not found")
        
        quest_data = json.loads(quest.data)
        sub_quests = quest_data.get("sub_quests", [])
        
        if not sub_quests:
            raise HTTPException(400, "No quest steps found")
        
    finally:
        db.close()
    
    async def generate_stream():
        try:
            # Get providers using factory
            reasoning_provider = get_reasoning_provider(use_perplexity=usePerplexityReasoning)
            search_provider = get_search_provider() if usePerplexity else None
            
            all_steps = []
            previous_context = ""  # Accumulated context from previous steps
            
            # ========================================
            # STEP 0: Single Perplexity search for ALL steps (coherent context)
            # ========================================
            web_references = ""
            if search_provider:
                # Build comprehensive search query covering all steps
                all_titles = [sq.get("title", f"Step {sq.get('step', 0)}") for sq in sub_quests]
                all_relations = [sq.get("relation_to_problem", "") for sq in sub_quests if sq.get("relation_to_problem")]
                main_topic = quest_data.get("title", "") or quest_data.get("problem_title", "") or all_titles[0]
                
                # Create a unified search covering the entire problem
                search_topic = f"{main_topic}: {', '.join(all_titles[:3])}"
                search_context = f"""This is a multi-step problem covering:
{chr(10).join([f"- Step {i+1}: {t}" for i, t in enumerate(all_titles)])}

Main concepts: {', '.join(list(set(all_relations))[:3]) if all_relations else main_topic}"""
                
                yield f"data: {json.dumps({'type': 'search', 'data': {'step': 0, 'topic': f'Searching: {search_topic[:50]}...'}})}\\n\\n"
                
                search_result = await search_provider.search(search_topic, search_context)
                if search_result:
                    web_references = f"""
### 📚 Web References (from Perplexity) - USE THIS DATA FOR ALL STEPS:
{search_result[:3000]}

**IMPORTANT**: Use the SAME real-world example dataset above for ALL steps below.
Each step should build on the previous step's results using this consistent dataset.
"""
                    yield f"data: {json.dumps({'type': 'search_complete', 'data': {'chars': len(search_result)}})}\\n\\n"
            
            # ========================================
            # STEPS 1-N: Generate reasoning for each step using same context
            # ========================================
            for sq in sub_quests:
                step = sq.get("step", 0)
                title = sq.get("title", f"Step {step}")
                relation = sq.get("relation_to_problem", "")
                math_content = sq.get("math_content", {})
                key_formulas = sq.get("key_formulas", [])
                exercise = sq.get("exercise", {})
                test_cases = exercise.get("test_cases", [])
                function_signature = exercise.get("function_signature", "")
                
                # Build context for this step
                formulas_text = "\n".join([
                    f"- {f.get('name', '')}: {f.get('latex', '')} ({f.get('description', '')})"
                    for f in key_formulas
                ])
                
                # Get first test case as example for computation
                example_input = test_cases[0].get("input", "") if test_cases else ""
                example_output = test_cases[0].get("expected", "") if test_cases else ""
                
                # Build prompt with previous context for correlated steps
                context_section = ""
                if previous_context:
                    context_section = f"""
### Previous Steps Summary (USE THESE RESULTS - CONTINUE THE CALCULATION):
{previous_context}

**CRITICAL**: You MUST use the computed values from previous steps. Continue the calculation chain.
"""
                

                prompt = f"""Step {step} of {len(sub_quests)}: {title}
{context_section}
{web_references}
Relation to main problem: {relation}
Definition: {math_content.get('definition', '')}
Key Formulas:
{formulas_text}

Function: {function_signature}
Example Test Case:
- Input: {example_input}
- Expected Output: {example_output}

Now, explain this step by:
1. **Concept**: What mathematical concept is being used in this step
2. **Formula Application**: Show the formula and explain each variable
3. **Step-by-Step Computation**: Using the example input above, compute the result step-by-step:
   - Parse the input data
   - **IMPORTANT**: When showing example data, use REAL-WORLD descriptive values instead of abstract ones.
     For example, instead of {{'A': 'x', 'B': '1'}}, use something like:
     {{'Weather': 'Sunny', 'Play': 'Yes'}}, {{'Age': 25, 'Income': 'High'}}, or {{'Size': 'Large', 'Color': 'Red'}}
   - Apply the formula with actual numbers from the input
   - Show intermediate calculations
   - Arrive at the expected output
4. **Key Result**: State the computed value clearly (this will be used in the next step)
5. **Connection to Next Step**: How this result feeds into the next step

Use LaTeX notation ($...$ for inline, $$...$$ for display math). Be thorough in the computation."""

                system_prompt = f"""You are a math computation specialist performing Step {step} of {len(sub_quests)}.

SEQUENTIAL COMPUTATION RULES:
- This is Step {step} of a {len(sub_quests)}-step sequential calculation
- If web references provided a real-world dataset (e.g., Weather/Tennis), use that SAME dataset
- If previous steps computed values, you MUST use those exact values - do NOT recompute from scratch
- Your output feeds into the next step, so state your final result clearly

ROLE SEPARATION:
- Web references contain: formulas, definitions, and real-world example data
- YOUR JOB: Take those formulas and compute exact numerical results step-by-step

COMPUTATION GUIDELINES:
1. Use the EXACT formulas from web references (if available)
2. Use the SAME real-world sample data throughout all steps (e.g., Weather=Sunny, Play=Yes)
3. Show ALL intermediate calculations with actual numbers
4. Use LaTeX for formulas ($...$ inline, $$...$$ display)
5. Reference previous step results by their exact computed values
6. End with a clear "**Result for Step {step}:**" statement

DO NOT explain theory - just COMPUTE using the consistent dataset."""

                # Generate reasoning using the selected provider
                reasoning = await reasoning_provider.generate_reasoning(prompt, system_prompt)
                if reasoning is None:
                    reasoning = f"[Error generating reasoning for step {step}]"
                step_data = {
                    "step": step,
                    "title": title,
                    "reasoning": reasoning
                }
                all_steps.append(step_data)
                
                # Extract key results for next step context (summarize this step)
                previous_context += f"""
**Step {step} - {title}**:
- Function: `{function_signature}`
- Input: `{example_input}`
- Output: `{example_output}`
- Key concept: {relation[:100] if relation else title}
"""
                
                # Stream this step
                yield f"data: {json.dumps({'type': 'step', 'data': step_data})}\n\n"
            
            # Generate final summary connecting all steps
            steps_summary = "\n".join([
                f"Step {s['step']}: {s['title']} - {s['reasoning'][:100]}..."
                for s in all_steps
            ])
            
            summary_system_prompt = "You are a math tutor providing a concise summary of how all steps connect to solve the problem. Use LaTeX for formulas."
            summary_user_prompt = f"Summarize how these steps work together to solve the problem:\n{steps_summary}\n\nProvide a 2-3 sentence summary connecting all concepts."
            
            # Generate summary using the selected provider
            summary = await reasoning_provider.generate_reasoning(summary_user_prompt, summary_system_prompt)
            if summary is None:
                summary = "[Error generating summary]"
            yield f"data: {json.dumps({'type': 'summary', 'data': summary})}\n\n"
            
            # Save to database
            reasoning_data = {"steps": all_steps, "summary": summary}
            db = SessionLocal()
            try:
                new_reasoning = QuestReasoning(
                    problem_id=problem_id,
                    reasoning_data=json.dumps(reasoning_data),
                    created_by=user_id
                )
                db.add(new_reasoning)
                db.commit()
            finally:
                db.close()
            
            yield f"data: {json.dumps({'type': 'done', 'cached': False})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")
