"""
Comprehensive tests for Thesis Evaluator Module

Tests DCCEPS-based argument assessment including:
- Position detection
- Evidence quality assessment
- DCCEPS layer detection (1-4)
- Scoring accuracy
- Feedback generation
"""

import pytest
from src.evaluators.thesis import (
    ThesisEvaluator, 
    ThesisEvaluationResult,
    extract_thesis_components,
    ThesisComponents
)


class TestThesisComponents:
    """Test component extraction functionality"""
    
    def test_position_detection_hero(self):
        text = "I believe Jonas is more of a hero than a victim."
        components = extract_thesis_components(text)
        assert components.position == "hero"
    
    def test_position_detection_victim(self):
        text = "Jonas is more of a victim because he suffered alone."
        components = extract_thesis_components(text)
        assert components.position == "victim"
    
    def test_position_strength_strong(self):
        text = "I strongly believe that Jonas is a victim."
        components = extract_thesis_components(text)
        assert components.position_strength == "strong"
    
    def test_position_strength_implicit(self):
        text = "Jonas is more of a victim than a hero."
        components = extract_thesis_components(text)
        assert components.position_strength == "implicit"
    
    def test_position_unclear(self):
        text = "Jonas is a character in the book."
        components = extract_thesis_components(text)
        assert components.position == "unclear"


class TestDCCEPSLayers:
    """Test DCCEPS layer detection"""
    
    def test_layer_1_definition_only(self):
        text = "Jonas is a victim."
        components = extract_thesis_components(text)
        assert components.dcceps_layer == 1
        assert components.dcceps_label == "Definition"
    
    def test_layer_2_comparison(self):
        text = "Jonas is more of a victim than a hero because he suffered more than he helped."
        components = extract_thesis_components(text)
        assert components.dcceps_layer >= 2
    
    def test_layer_3_cause_effect(self):
        text = """Jonas is more of a victim because he was forced to receive memories. 
        This caused him to experience isolation. Therefore, his suffering outweighs his heroism."""
        components = extract_thesis_components(text)
        assert components.dcceps_layer >= 3
    
    def test_layer_4_with_counter_argument(self):
        text = """I believe Jonas is more of a victim than a hero. Although he saved Gabriel, 
        his suffering from receiving painful memories alone caused profound isolation. 
        However, some might argue he was heroic for escaping. Nevertheless, the evidence 
        shows he suffered more than he saved. Therefore, Jonas is ultimately more victim than hero."""
        components = extract_thesis_components(text)
        assert components.dcceps_layer == 4


class TestThesisScoring:
    """Test scoring functionality"""
    
    def test_short_response_capped(self):
        """Very short responses should not score above 3.0 on SM2"""
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is a victim because he suffered.")
        assert result.sm2_score <= 3.0
    
    def test_specific_evidence_higher_score(self):
        """Specific evidence should score higher than general"""
        evaluator = ThesisEvaluator()
        
        general = evaluator.evaluate("Jonas is a victim because he suffered in the community.")
        specific = evaluator.evaluate('Jonas is a victim because when he received the memory of warfare where "the boy died begging for water," he experienced pain nobody else could understand.')
        
        assert specific.sm1_score >= general.sm1_score
    
    def test_counter_argument_improves_sm3(self):
        """Counter-argument should improve SM3 score"""
        evaluator = ThesisEvaluator()
        
        no_counter = evaluator.evaluate("Jonas is a victim because he suffered alone.")
        with_counter = evaluator.evaluate("Jonas is a victim. Although he showed heroism by saving Gabriel, his suffering from isolation outweighs this.")
        
        assert with_counter.sm3_score >= no_counter.sm3_score
    
    def test_multiple_evidence_items_improves_score(self):
        """Multiple evidence items should score higher than single"""
        evaluator = ThesisEvaluator()
        
        single = evaluator.evaluate('Jonas is a victim because "he received painful memories."')
        multiple = evaluator.evaluate('Jonas is a victim because "he received painful memories" and when "the boy died begging for water," he experienced isolation.')
        
        assert multiple.sm1_score >= single.sm1_score


class TestFeedback:
    """Test feedback generation"""
    
    def test_dcceps_guidance_present(self):
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is a victim because he suffered.")
        assert 'dcceps_guidance' in result.feedback
        assert len(result.feedback['dcceps_guidance']) > 50
    
    def test_layer_specific_guidance(self):
        """Feedback should reference current layer and next steps"""
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is more of a victim than a hero.")
        
        # Should mention current layer
        assert f"Layer {result.dcceps_layer}" in result.feedback['dcceps_guidance'] or \
               result.dcceps_label in result.feedback['dcceps_guidance']
    
    def test_sm1_feedback_present(self):
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is a victim.")
        assert 'sm1' in result.feedback
        assert 'sm1_next' in result.feedback
    
    def test_sm2_feedback_present(self):
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is a victim.")
        assert 'sm2' in result.feedback
        assert 'sm2_next' in result.feedback
    
    def test_sm3_feedback_present(self):
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is a victim.")
        assert 'sm3' in result.feedback
        assert 'sm3_next' in result.feedback


class TestEvaluatorInterface:
    """Test main evaluator interface"""
    
    def test_evaluate_accepts_string(self):
        """evaluate() should accept string directly"""
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("I believe Jonas is more of a victim because he suffered alone.")
        assert isinstance(result, ThesisEvaluationResult)
        assert result.dcceps_layer >= 1
    
    def test_evaluate_accepts_dict(self):
        """evaluate() should also accept dict for compatibility"""
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate({'transcription': "I believe Jonas is more of a victim because he suffered alone."})
        assert isinstance(result, ThesisEvaluationResult)
        assert result.dcceps_layer >= 1
    
    def test_evaluate_batch(self):
        """evaluate_batch() should process multiple texts"""
        evaluator = ThesisEvaluator()
        texts = {
            "Student1": "Jonas is a victim because he suffered.",
            "Student2": "Jonas is more of a hero because he saved Gabriel."
        }
        results = evaluator.evaluate_batch(texts)
        assert len(results) == 2
        assert "Student1" in results
        assert "Student2" in results
        assert isinstance(results["Student1"], ThesisEvaluationResult)
    
    def test_generate_report(self):
        """generate_report() should produce markdown"""
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas is a victim because he suffered.")
        report = evaluator.generate_report(result, "Test Student")
        assert "# Thesis Quality Report: Test Student" in report
        assert "SM1:" in report
        assert "SM2:" in report
        assert "SM3:" in report


class TestComparativeSummary:
    """Test comparative summary functionality"""
    
    def test_format_comparative_summary(self):
        """format_comparative_summary() should produce table"""
        from src.evaluators.thesis import format_comparative_summary
        
        evaluator = ThesisEvaluator()
        results = {
            "Student1": evaluator.evaluate("Jonas is a victim."),
            "Student2": evaluator.evaluate("Jonas is more of a hero because he saved Gabriel.")
        }
        
        summary = format_comparative_summary(results)
        assert "# Thesis Quality: Comparative Summary" in summary
        assert "Student1" in summary
        assert "Student2" in summary
        assert "DCCEPS Layer" in summary


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_string(self):
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("")
        assert result.dcceps_layer == 0
        assert result.components.position == "unclear"
    
    def test_very_short_text(self):
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("Jonas.")
        assert result.dcceps_layer <= 1
    
    def test_contradictory_statements(self):
        """Test detection of contradictions"""
        evaluator = ThesisEvaluator()
        text = "Jonas is a victim. Actually, he is not really a victim."
        result = evaluator.evaluate(text)
        # Should detect contradiction and potentially penalize
        assert result.sm2_score <= 4.0  # Contradiction should cap score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
