#!/usr/bin/env python3
"""
Test script for llm_sidechannel package.

This script demonstrates basic functionality of the package.
"""

import sys
sys.path.insert(0, 'src')

from llm_sidechannel.core.config import load_model_config, list_available_presets
from llm_sidechannel.models.mixtral_wrapper import MixtralWrapper
from llm_sidechannel.analysis.expert_usage import ExpertUsageAnalyzer


def test_config():
    """Test configuration loading."""
    print("=== Testing Configuration ===")
    
    # List available presets
    presets = list_available_presets()
    print("Available presets:")
    for preset, description in presets.items():
        print(f"  {preset}: {description}")
    
    # Load a configuration
    config = load_model_config(preset="mixtral-8x7b-4bit")
    print(f"\nLoaded config: {config.model_name}")
    print(f"Device: {config.device}")
    print(f"4-bit: {config.load_in_4bit}")
    print(f"Temperature: {config.temperature}")


def test_expert_analyzer():
    """Test expert usage analyzer."""
    print("\n=== Testing Expert Usage Analyzer ===")
    
    analyzer = ExpertUsageAnalyzer(num_experts=8)
    
    # Test with sample data
    expert_usage = {0: 15, 1: 8, 2: 12, 3: 3, 4: 20, 5: 7, 6: 14, 7: 2}
    
    analysis = analyzer.analyze_expert_distribution(expert_usage)
    
    print(f"Total usage: {analysis['total_usage']}")
    print(f"Entropy: {analysis['entropy']:.3f}")
    print(f"Gini coefficient: {analysis['gini_coefficient']:.3f}")
    print(f"Load balance score: {analysis['load_balance_score']:.3f}")
    print(f"Most used expert: #{analysis['most_used_expert'][0]} ({analysis['most_used_expert'][1]} times)")
    print(f"Analysis: {analysis['analysis']}")


def test_model_loading():
    """Test model loading (if resources allow)."""
    print("\n=== Testing Model Loading ===")
    
    try:
        # Use a small model or skip if resources are limited
        config = load_model_config(
            model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
            load_in_4bit=True,
            max_new_tokens=20
        )
        
        print(f"Would load model: {config.model_name}")
        print(f"Configuration: 4-bit={config.load_in_4bit}, max_tokens={config.max_new_tokens}")
        print("Note: Actual model loading skipped due to resource requirements")
        
        # If you have sufficient resources, uncomment the following:
        # wrapper = MixtralWrapper(config)
        # response = wrapper.query("Hello, how are you?", analyze_routing=True)
        # print(f"Response: {response.text}")
        # print(f"Expert usage: {response.expert_usage}")
        
    except Exception as e:
        print(f"Model loading test skipped: {e}")


def main():
    """Main test function."""
    print("Testing llm_sidechannel package...")
    
    test_config()
    test_expert_analyzer()
    test_model_loading()
    
    print("\n=== Test Complete ===")
    print("Package structure created successfully!")
    print("\nTo use the package:")
    print("1. Install dependencies: nix develop")
    print("2. Query model: python -m llm_sidechannel.tools.query --preset mixtral-8x7b-4bit --prompt 'Hello!'")
    print("3. Analyze patterns: python -m llm_sidechannel.tools.analyze_moe --preset mixtral-8x7b-4bit --prompts 'Hello' 'How are you?'")


if __name__ == "__main__":
    main() 