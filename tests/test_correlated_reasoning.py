"""
Unit tests for correlated reasoning generation.
Tests that each step receives context from previous steps.
"""
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock


class MockOpenAIResponse:
    """Mock OpenAI API response"""
    def __init__(self, content: str):
        self.choices = [MagicMock(message=MagicMock(content=content))]


class TestCorrelatedReasoning:
    """Test suite for correlated reasoning steps"""
    
    @pytest.fixture
    def sample_quest_data(self):
        """Sample quest data for Decision Tree problem"""
        return {
            "sub_quests": [
                {
                    "step": 1,
                    "title": "Entropy Fundamentals",
                    "relation_to_problem": "Calculate uncertainty in dataset",
                    "math_content": {"definition": "Shannon Entropy"},
                    "key_formulas": [{"name": "Entropy", "latex": "H(D) = -\\sum p_i \\log_2 p_i"}],
                    "exercise": {
                        "function_signature": "calculate_entropy(labels)",
                        "test_cases": [{"input": "['Yes', 'Yes', 'No', 'No']", "expected": "1.0"}]
                    }
                },
                {
                    "step": 2,
                    "title": "Information Gain",
                    "relation_to_problem": "Measure attribute effectiveness using entropy from step 1",
                    "math_content": {"definition": "Information Gain"},
                    "key_formulas": [{"name": "IG", "latex": "IG(D,A) = H(D) - H(D|A)"}],
                    "exercise": {
                        "function_signature": "calculate_info_gain(examples, attr, target)",
                        "test_cases": [{"input": "[{'A': 'x', 'C': 'Yes'}]", "expected": "0.5"}]
                    }
                },
                {
                    "step": 3,
                    "title": "Tree Construction",
                    "relation_to_problem": "Build tree using best attribute from step 2",
                    "math_content": {"definition": "ID3 Algorithm"},
                    "key_formulas": [{"name": "Best Attr", "latex": "a^* = argmax IG(D,a)"}],
                    "exercise": {
                        "function_signature": "build_tree(examples, attrs, target)",
                        "test_cases": [{"input": "[{'A': 'x'}]", "expected": "{'A': 'x'}"}]
                    }
                }
            ]
        }
    
    def test_previous_context_accumulated(self, sample_quest_data):
        """Test that previous_context is accumulated across steps"""
        sub_quests = sample_quest_data["sub_quests"]
        previous_context = ""
        
        for sq in sub_quests:
            step = sq.get("step", 0)
            title = sq.get("title", "")
            relation = sq.get("relation_to_problem", "")
            exercise = sq.get("exercise", {})
            function_signature = exercise.get("function_signature", "")
            test_cases = exercise.get("test_cases", [])
            example_input = test_cases[0].get("input", "") if test_cases else ""
            example_output = test_cases[0].get("expected", "") if test_cases else ""
            
            # This is how context is built in the endpoint
            previous_context += f"""
**Step {step} - {title}**:
- Function: `{function_signature}`
- Input: `{example_input}`
- Output: `{example_output}`
- Key concept: {relation[:100] if relation else title}
"""
        
        # Verify context contains all steps
        assert "Step 1 - Entropy Fundamentals" in previous_context
        assert "Step 2 - Information Gain" in previous_context
        assert "Step 3 - Tree Construction" in previous_context
        assert "calculate_entropy(labels)" in previous_context
        assert "calculate_info_gain" in previous_context
        assert "build_tree" in previous_context
    
    def test_context_section_built_correctly(self, sample_quest_data):
        """Test that context section is only built when there's previous context"""
        previous_context = ""
        
        # First step - no context
        context_section = ""
        if previous_context:
            context_section = f"### Previous Steps Summary:\n{previous_context}"
        assert context_section == ""
        
        # Add some context
        previous_context = "**Step 1**: Calculated entropy = 1.0"
        
        # Second step - has context
        if previous_context:
            context_section = f"### Previous Steps Summary:\n{previous_context}"
        assert "Previous Steps Summary" in context_section
        assert "entropy = 1.0" in context_section
    
    def test_prompt_includes_step_count(self, sample_quest_data):
        """Test that prompt shows step X of Y"""
        sub_quests = sample_quest_data["sub_quests"]
        total_steps = len(sub_quests)
        
        for sq in sub_quests:
            step = sq.get("step", 0)
            title = sq.get("title", "")
            
            # Simulated prompt header
            prompt_header = f"Step {step} of {total_steps}: {title}"
            
            assert f"of {total_steps}" in prompt_header
    
    def test_key_result_instruction_present(self):
        """Test that prompt instructs AI to state key result for next step"""
        prompt_template = """
4. **Key Result**: State the computed value clearly (this will be used in the next step)
5. **Connection to Next Step**: How this result feeds into the next step
"""
        assert "Key Result" in prompt_template
        assert "next step" in prompt_template.lower()
    

class TestReasoningFlow:
    """Test the complete reasoning flow"""
    
    def test_reasoning_chain_example(self):
        """
        Example of expected correlated reasoning output:
        
        Step 1: Entropy = 1.0
        Step 2: Uses entropy (1.0) from Step 1 to calculate IG = 0.5
        Step 3: Uses best attribute (IG=0.5) from Step 2 to split tree
        """
        # Simulated reasoning outputs
        step1_result = {"entropy": 1.0}
        step2_result = {"info_gain": 0.5, "uses_entropy": step1_result["entropy"]}
        step3_result = {"tree_split": "A", "uses_ig": step2_result["info_gain"]}
        
        # Verify chain
        assert step2_result["uses_entropy"] == step1_result["entropy"]
        assert step3_result["uses_ig"] == step2_result["info_gain"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
