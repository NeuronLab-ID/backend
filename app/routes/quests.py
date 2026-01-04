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
from app.models.schemas import QuestExecuteRequest, QuestCreateRequest, QuestProgressSaveRequest, QuestReasoningRequest, FixMermaidRequest
from app.services.executor import execute_code
from app.services import get_provider, get_search_provider, get_reasoning_provider
from app.services.hint_generator import AI_BACKEND, create_client, AI_MODEL  # For backward compatibility


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
                # Emit web references first if available (for images)
                if cached_data.get("web_references"):
                    yield f"data: {json.dumps({'type': 'search_result', 'data': {'content': cached_data['web_references']}})}\n\n"
                    yield f"data: {json.dumps({'type': 'search_complete', 'data': {'chars': len(cached_data['web_references'])}})}\n\n"
                
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
                
                yield f"data: {json.dumps({'type': 'search', 'data': {'step': 0, 'topic': f'Searching: {search_topic[:50]}...'}})}\n\n"
                
                search_result = await search_provider.search(search_topic, search_context)
                if search_result:
                    # Send full search result to frontend (includes images)
                    yield f"data: {json.dumps({'type': 'search_result', 'data': {'content': search_result}})}\n\n"
                    
                    # Use truncated version for reasoning context (increased from 3000 to 8000)
                    web_references = f"""
### 📚 Web References (from Perplexity) - USE THIS DATA FOR ALL STEPS:
{search_result}

**IMPORTANT**: Use the SAME real-world example dataset above for ALL steps below.
Each step should build on the previous step's results using this consistent dataset.
"""
                    yield f"data: {json.dumps({'type': 'search_complete', 'data': {'chars': len(search_result)}})}\n\n"
            
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

Now, explain this step with VISUAL AIDS for visual learners:

1. **Concept Overview**: What mathematical concept is being used (include a Mermaid flowchart if helpful)

2. **Visual Data Table**: Display the example data in a MARKDOWN TABLE:
   | Feature | Value 1 | Value 2 | ... |
   |---------|---------|---------|-----|
   Use REAL-WORLD descriptive values (e.g., Weather=Sunny, Play=Yes)

3. **Formula Application**: Show the formula with a visual breakdown:
   - Display the formula in LaTeX ($$...$$)
   - Create a Mermaid diagram showing data flow if applicable:
     ```mermaid
     graph LR
       A[Input] --> B[Process] --> C[Output]
     ```

4. **Step-by-Step Computation**: Show calculations in an organized way:
   - Use TABLES for intermediate results when appropriate
   - Show each calculation step clearly
   - Use $$...$$ for important formulas

5. **Visual Summary**: Include ONE of these visual aids:
   - **Mermaid Flowchart**: For algorithm steps
   - **Markdown Table**: For data transformations
   - **Tree Diagram** (using mermaid): For hierarchical data

6. **Key Result**: State the computed value clearly in a highlighted box
7. **Connection to Next Step**: How this result feeds into the next step

VISUAL REQUIREMENTS:
- Include at least ONE markdown table showing data
- Include at least ONE mermaid diagram (flowchart, graph, or tree)
- Use LaTeX notation ($...$ for inline, $$...$$ for display math)
- Make it easy to follow visually"""

                system_prompt = f"""You are a VISUAL LEARNING specialist performing Step {step} of {len(sub_quests)}.

YOU MUST INCLUDE VISUAL AIDS:
1. **Markdown Tables**: Show data in tabular format
2. **Mermaid Diagrams**: Include flowcharts, graphs, or trees
3. **LaTeX Formulas**: Use $$...$$ for display math

MERMAID EXAMPLES YOU CAN USE:
```mermaid
graph TD
    A[Start] --> B{{Decision}}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
```

```mermaid
graph LR
    Input --> Process --> Output
```

SEQUENTIAL COMPUTATION RULES:
- This is Step {step} of a {len(sub_quests)}-step sequential calculation
- If web references provided a real-world dataset (e.g., Weather/Tennis), use that SAME dataset
- If previous steps computed values, you MUST use those exact values
- Your output feeds into the next step, so state your final result clearly

VISUAL OUTPUT REQUIREMENTS:
1. Start with a brief concept overview
2. Show data in a MARKDOWN TABLE (required)
3. Include a MERMAID DIAGRAM showing the algorithm/data flow (required)
4. Use LaTeX for all formulas ($...$ inline, $$...$$ display)
5. Show step-by-step calculations with intermediate tables
6. End with a clear visual summary and "**Result for Step {step}:**"

IMPORTANT: Make the explanation VISUAL and easy to scan. Use diagrams and tables extensively."""

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
            
            # Save to database (include web_references for images)
            reasoning_data = {"steps": all_steps, "summary": summary, "web_references": web_references}
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


@router.post("/fix-mermaid")
async def fix_mermaid_code(request: FixMermaidRequest, user_id: int = Depends(get_current_user)):
    """Use AI to fix invalid Mermaid diagram code."""
    try:
        client = create_client()
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a Mermaid diagram syntax expert. Fix the provided Mermaid diagram code.

Common issues to fix:
1. Newlines inside node labels - use <br/> instead or put on single line
2. Unicode subscripts (like ₁, ₂) - replace with regular text
3. Unquoted special characters in labels - add quotes around labels with special chars
4. Missing quotes around labels with spaces/special characters
5. Invalid node IDs - ensure IDs are alphanumeric with underscores only
6. Syntax errors in edges or subgraphs

Return ONLY the fixed Mermaid code, nothing else. No explanation, no markdown code blocks."""
                },
                {
                    "role": "user",
                    "content": f"""Fix this Mermaid diagram. Error: {request.error}

Original code:
{request.code}

Return only the fixed Mermaid code:"""
                }
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        fixed_code = response.choices[0].message.content or request.code
        
        # Clean up the response (remove markdown code blocks if present)
        fixed_code = fixed_code.strip()
        if fixed_code.startswith("```"):
            lines = fixed_code.split("\n")
            fixed_code = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        
        return {"fixed_code": fixed_code}
        
    except Exception as e:
        # Return original code on error
        return {"fixed_code": request.code, "error": str(e)}


@router.post("/quest/export-markdown/{problem_id}")
async def export_reasoning_markdown(problem_id: int, use_ai: bool = False, force: bool = False, user_id: int = Depends(get_current_user)):
    """
    Export reasoning as formatted markdown.
    
    Args:
        problem_id: Problem ID
        use_ai: If True, use Perplexity AI to enhance formatting with proper LaTeX
        force: If True, regenerate even if cached version exists
    """
    from app.models.db import Problem, ReasoningExport
    
    db = SessionLocal()
    try:
        # Check for cached export first (if use_ai and not force)
        if use_ai and not force:
            cached_export = db.query(ReasoningExport).filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == 'markdown'
            ).first()
            
            if cached_export:
                return {"markdown": cached_export.content, "enhanced": True, "cached": True}
        
        # Get cached reasoning
        reasoning = db.query(QuestReasoning).filter(
            QuestReasoning.problem_id == problem_id
        ).first()
        
        if not reasoning:
            raise HTTPException(404, "No reasoning found for this problem. Generate reasoning first.")
        
        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])
        summary = reasoning_data.get("summary", "")
        web_references = reasoning_data.get("web_references", "")
        
        # Get problem title
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        problem_name = problem.title if problem else f"Problem {problem_id}"
        
    finally:
        db.close()
    
    # Convert LaTeX delimiters for Google Docs compatibility
    def convert_latex(text: str) -> str:
        import re
        # Convert \(...\) to $...$
        result = re.sub(r'\\\((.+?)\\\)', r'$\1$', text, flags=re.DOTALL)
        # Convert \[...\] to $$...$$
        result = re.sub(r'\\\[(.+?)\\\]', r'$$\1$$', result, flags=re.DOTALL)
        return result
    
    if use_ai:
        # Use Perplexity AI to enhance formatting
        try:
            search_provider = get_search_provider()
            if not search_provider or not search_provider.is_configured():
                raise HTTPException(503, "Perplexity AI is not configured. Using quick export.")
            
            # Format all steps for AI enhancement
            steps_text = "\n\n".join([
                f"## Step {s['step']}: {s['title']}\n{s['reasoning']}"
                for s in steps
            ])
            
            enhance_prompt = f"""Reformat this mathematical solution reasoning for Google Docs compatibility.

REQUIREMENTS:
1. Use $...$ for inline math (e.g., $x = 5$)
2. Use $$...$$ for display math on separate lines (e.g., $$\\frac{{a}}{{b}}$$)
3. Clean up any LaTeX syntax errors
4. Ensure all mathematical expressions are properly formatted
5. Keep all content but improve readability
6. Format tables properly using markdown syntax

CONTENT TO REFORMAT:
{steps_text}

SUMMARY:
{summary}

Return the reformatted content maintaining the same structure (## Step N: Title format)."""

            enhanced = await search_provider.search(enhance_prompt, "Format mathematical content for Google Docs with LaTeX")
            
            if enhanced:
                # Parse enhanced content back into steps
                from datetime import datetime
                current_date = datetime.now().strftime("%B %d, %Y")
                
                markdown = f"# {problem_name} - Solution Reasoning\n\n"
                markdown += f"> Generated by NeuronLab AI (Enhanced) | {current_date}\n"
                markdown += "> Open in Google Docs with Auto-LaTeX Equations add-on for best experience\n\n"
                markdown += convert_latex(enhanced)
                
                if web_references:
                    markdown += "\n\n---\n\n## References\n\n"
                    markdown += convert_latex(web_references)
                
                # Save to database
                db = SessionLocal()
                try:
                    # Delete existing if force regenerate
                    existing = db.query(ReasoningExport).filter(
                        ReasoningExport.problem_id == problem_id,
                        ReasoningExport.export_type == 'markdown'
                    ).first()
                    if existing:
                        db.delete(existing)
                    
                    new_export = ReasoningExport(
                        problem_id=problem_id,
                        export_type='markdown',
                        content=markdown,
                        ai_model='pplx_alpha',
                        created_by=user_id
                    )
                    db.add(new_export)
                    db.commit()
                finally:
                    db.close()
                
                return {"markdown": markdown, "enhanced": True, "cached": False}
                
        except Exception as e:
            # Fall back to quick export on error
            pass
    
    # Quick export (no AI)
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")
    
    markdown = f"# {problem_name} - Solution Reasoning\n\n"
    markdown += f"> Generated by NeuronLab AI | {current_date}\n"
    markdown += "> Open in Google Docs with Auto-LaTeX Equations add-on for best experience\n\n"
    
    for step in steps:
        markdown += f"## Step {step['step']}: {step['title']}\n\n"
        markdown += convert_latex(step['reasoning']) + "\n\n"
    
    if summary:
        markdown += "---\n\n## Summary\n\n"
        markdown += convert_latex(summary) + "\n\n"
    
    if web_references:
        markdown += "---\n\n## References\n\n"
        markdown += convert_latex(web_references) + "\n"
    
    return {"markdown": markdown, "enhanced": False}


@router.post("/quest/export-latex/{problem_id}")
async def export_reasoning_latex(problem_id: int, useSonnet: bool = False, force: bool = False, user_id: int = Depends(get_current_user)):
    """
    Export reasoning as valid LaTeX (.tex) document using AI.
    
    Args:
        useSonnet: If True, use Claude 4.5 Sonnet + Web Search for enhanced LaTeX generation
                   with web-validated syntax. Slower but more accurate.
        force: If True, regenerate even if cached version exists
    
    Uses Perplexity AI to ensure valid pdfLaTeX syntax - prevents compilation errors.
    """
    from app.models.db import Problem, ReasoningExport
    
    export_type = 'latex_sonnet' if useSonnet else 'latex'
    
    db = SessionLocal()
    try:
        # Check for cached export first (if not force)
        if not force:
            cached_export = db.query(ReasoningExport).filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type
            ).first()
            
            if cached_export:
                return {"latex": cached_export.content, "ai_generated": True, "model": cached_export.ai_model, "cached": True}
        
        # Get cached reasoning
        reasoning = db.query(QuestReasoning).filter(
            QuestReasoning.problem_id == problem_id
        ).first()
        
        if not reasoning:
            raise HTTPException(404, "No reasoning found for this problem. Generate reasoning first.")
        
        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])
        summary = reasoning_data.get("summary", "")
        
        # Get problem title
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        problem_name = problem.title if problem else f"Problem {problem_id}"
        
    finally:
        db.close()
    
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Build content for AI to convert
    raw_content = ""
    for step in steps:
        raw_content += f"## Step {step['step']}: {step['title']}\n\n{step['reasoning']}\n\n"
    
    if summary:
        raw_content += f"## Summary\n\n{summary}\n\n"
    
    # Use AI to generate valid LaTeX
    try:
        if useSonnet:
            # Use Claude 4.5 Sonnet with web search - higher quality, slower
            reasoning_provider = get_reasoning_provider(use_perplexity=True)
            if reasoning_provider and reasoning_provider.is_configured():
                sonnet_prompt = f"""You are a LaTeX expert. Convert this mathematical reasoning into a VALID pdfLaTeX document.

IMPORTANT: Search the web to verify LaTeX syntax for any complex mathematical notation.
- Search for correct LaTeX syntax for matrices, integrals, summations, fractions
- Search for proper package requirements for special symbols
- Validate that all environments (equation, align, lstlisting) are correctly used

CRITICAL OUTPUT REQUIREMENTS:
1. Output ONLY valid LaTeX code - no markdown wrappers, no explanations
2. Start with \\documentclass{{article}}
3. Include packages: amsmath, amssymb, amsthm, hyperref, listings, graphicx, xcolor, geometry, booktabs
4. ESCAPE all special characters: & → \\&, % → \\%, # → \\#, _ → \\_
5. Use \\section{{}} for headers, \\textbf{{}} for bold, \\textit{{}} for italic
6. Math: \\( \\) for inline, \\[ \\] or $$ for display equations
7. Code blocks: \\begin{{lstlisting}} ... \\end{{lstlisting}}
8. Tables: Use tabular with proper column specs
9. NO undefined control sequences - verify each LaTeX command exists
10. Must compile in pdfLaTeX without errors

DOCUMENT METADATA:
- Title: {problem_name} - Solution Reasoning  
- Author: Generated by NeuronLab AI (Sonnet Enhanced)
- Date: {current_date}

CONTENT TO CONVERT:
{raw_content}

Output the complete, compilable .tex file:"""

                sonnet_system = """You are a LaTeX documentation expert. Your task is to produce ONLY valid, compilable pdfLaTeX code.
Search the web to verify any LaTeX syntax you are unsure about. Common issues to avoid:
- Missing package declarations for special symbols
- Unescaped special characters (&, %, #, _, {, })
- Mismatched braces or environments
- Invalid math mode syntax"""

                latex_result = await reasoning_provider.generate_reasoning(sonnet_prompt, sonnet_system)
                
                if latex_result:
                    latex = latex_result.strip()
                    # Clean markdown wrappers if present
                    if latex.startswith("```"):
                        lines = latex.split("\n")
                        latex = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                    
                    # Ensure proper document structure
                    if not latex.strip().startswith("\\documentclass"):
                        latex = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{amsmath,amssymb,amsthm}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{listings}}
\\usepackage{{xcolor}}
\\usepackage{{geometry}}
\\usepackage{{booktabs}}
\\geometry{{margin=1in}}
\\lstset{{basicstyle=\\ttfamily\\small,breaklines=true,frame=single,backgroundcolor=\\color{{gray!10}}}}
\\title{{{problem_name.replace('#', '').replace('$', '').replace('%', '').replace('&', 'and').replace('_', ' ')} -- Solution Reasoning}}
\\author{{Generated by NeuronLab AI (Sonnet Enhanced)}}
\\date{{{current_date}}}
\\begin{{document}}
\\maketitle

{latex}"""
                    
                    if "\\end{document}" not in latex:
                        latex += "\n\\end{document}\n"
                    
                    # Save to database
                    db = SessionLocal()
                    try:
                        existing = db.query(ReasoningExport).filter(
                            ReasoningExport.problem_id == problem_id,
                            ReasoningExport.export_type == 'latex_sonnet'
                        ).first()
                        if existing:
                            db.delete(existing)
                        
                        new_export = ReasoningExport(
                            problem_id=problem_id,
                            export_type='latex_sonnet',
                            content=latex,
                            ai_model='sonnet',
                            created_by=user_id
                        )
                        db.add(new_export)
                        db.commit()
                    finally:
                        db.close()
                    
                    return {"latex": latex, "ai_generated": True, "model": "sonnet", "cached": False}
        
        # Default: Use search provider (pplx_alpha) - faster
        search_provider = get_search_provider()
        if search_provider and search_provider.is_configured():
            latex_prompt = f"""Convert the following mathematical reasoning content into a VALID pdfLaTeX document.

CRITICAL REQUIREMENTS:
1. Output ONLY the LaTeX code, no markdown, no explanation
2. Start with \\documentclass{{article}}
3. Include all necessary packages: amsmath, amssymb, amsthm, hyperref, listings, graphicx, xcolor, geometry
4. Properly escape all special LaTeX characters: &, %, $, #, _, {{}}, ~, ^, \\
5. Convert markdown headers to \\section{{}} and \\subsection{{}}
6. Convert **bold** to \\textbf{{}} and *italic* to \\textit{{}}
7. Convert `code` to \\texttt{{}}
8. Ensure all math expressions use proper LaTeX: \\( \\) for inline, \\[ \\] for display
9. Convert markdown code blocks to lstlisting environment
10. Make sure the document compiles without errors in pdfLaTeX

TITLE: {problem_name} - Solution Reasoning
DATE: {current_date}
AUTHOR: Generated by NeuronLab AI

CONTENT TO CONVERT:
{raw_content}

Output the complete .tex file that will compile without errors:"""

            latex_result = await search_provider.search(latex_prompt, "Generate valid pdfLaTeX document")
            
            if latex_result:
                # Clean up the result - extract LaTeX code if wrapped in markdown
                latex = latex_result.strip()
                if latex.startswith("```"):
                    lines = latex.split("\n")
                    # Remove first line (```latex or ```) and last line (```)
                    latex = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                
                # Ensure it starts with documentclass
                if not latex.strip().startswith("\\documentclass"):
                    # Prepend standard preamble if AI didn't include it
                    preamble = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{amsmath,amssymb,amsthm}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{listings}}
\\usepackage{{xcolor}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}
\\lstset{{basicstyle=\\ttfamily\\small,breaklines=true,frame=single,backgroundcolor=\\color{{gray!10}}}}
\\title{{{problem_name.replace('#', '').replace('$', '').replace('%', '').replace('&', 'and').replace('_', ' ')} -- Solution Reasoning}}
\\author{{Generated by NeuronLab AI}}
\\date{{{current_date}}}
\\begin{{document}}
\\maketitle

"""
                    latex = preamble + latex
                
                # Ensure it ends with end document
                if "\\end{document}" not in latex:
                    latex += "\n\\end{document}\n"
                
                # Save to database
                db = SessionLocal()
                try:
                    existing = db.query(ReasoningExport).filter(
                        ReasoningExport.problem_id == problem_id,
                        ReasoningExport.export_type == 'latex'
                    ).first()
                    if existing:
                        db.delete(existing)
                    
                    new_export = ReasoningExport(
                        problem_id=problem_id,
                        export_type='latex',
                        content=latex,
                        ai_model='pplx_alpha',
                        created_by=user_id
                    )
                    db.add(new_export)
                    db.commit()
                finally:
                    db.close()
                
                return {"latex": latex, "ai_generated": True, "cached": False}
    
    except Exception as e:
        print(f"AI LaTeX generation failed: {e}")
    
    # Fallback: Generate basic LaTeX without AI
    safe_title = problem_name.replace('#', '').replace('$', '').replace('%', '').replace('&', 'and').replace('_', ' ')
    
    latex = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{amsmath,amssymb,amsthm}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{listings}}
\\usepackage{{xcolor}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}
\\lstset{{basicstyle=\\ttfamily\\small,breaklines=true,frame=single,backgroundcolor=\\color{{gray!10}}}}
\\title{{{safe_title} -- Solution Reasoning}}
\\author{{Generated by NeuronLab AI}}
\\date{{{current_date}}}
\\begin{{document}}
\\maketitle

"""
    
    for step in steps:
        safe_step_title = step['title'].replace('#', '').replace('$', '').replace('%', '').replace('&', 'and').replace('_', ' ')
        latex += f"\\section{{Step {step['step']}: {safe_step_title}}}\n\n"
        
        # Basic conversion of reasoning content
        content = step['reasoning']
        # Escape special characters (basic)
        for char in ['&', '%', '#', '_']:
            content = content.replace(char, '\\' + char)
        # Convert markdown bold/italic
        import re
        content = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', content)
        content = re.sub(r'\*([^*]+)\*', r'\\textit{\1}', content)
        # Convert inline code
        content = re.sub(r'`([^`]+)`', r'\\texttt{\1}', content)
        
        latex += content + "\n\n"
    
    if summary:
        latex += "\\section{Summary}\n\n"
        summary_content = summary
        for char in ['&', '%', '#', '_']:
            summary_content = summary_content.replace(char, '\\' + char)
        latex += summary_content + "\n\n"
    
    latex += "\\end{document}\n"
    
    return {"latex": latex, "ai_generated": False}

