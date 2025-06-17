#!/usr/bin/env python3
"""Analyze Mixtral MoE routing patterns."""

import argparse
import sys
import json
from ..core.config import load_model_config
from ..models.mixtral_wrapper import MixtralWrapper
from ..analysis.expert_usage import ExpertUsageAnalyzer


def analyze_prompts(prompts, wrapper, analyzer):
    """Analyze multiple prompts and compare routing patterns."""
    results = []
    usage_patterns = []
    
    for i, prompt in enumerate(prompts):
        print(f"Processing prompt {i+1}/{len(prompts)}: {prompt[:50]}...")
        
        response = wrapper.query(prompt, analyze_routing=True)
        analysis = wrapper.analyze_response(response)
        
        if analysis and response.expert_usage:
            usage_patterns.append(response.expert_usage)
            
            expert_analysis = analyzer.analyze_expert_distribution(response.expert_usage)
            
            results.append({
                'prompt': prompt,
                'response': response.text,
                'expert_usage': response.expert_usage,
                'expert_analysis': expert_analysis
            })
        else:
            results.append({
                'prompt': prompt,
                'response': response.text,
                'expert_usage': None,
                'expert_analysis': None
            })
    
    # Compare usage patterns
    comparison = None
    if len(usage_patterns) >= 2:
        comparison = analyzer.compare_usage_patterns(
            usage_patterns, 
            labels=[f"Prompt {i+1}" for i in range(len(usage_patterns))]
        )
    
    return results, comparison


def main():
    """Main function for the MoE analysis tool."""
    parser = argparse.ArgumentParser(description="Analyze Mixtral MoE routing patterns")
    
    parser.add_argument('--preset', type=str, help='Configuration preset to use')
    parser.add_argument('--model', type=str, help='Model name')
    parser.add_argument('--device', type=str, help='Device to use')
    parser.add_argument('--load-in-4bit', action='store_true', help='Load in 4-bit precision')
    parser.add_argument('--prompts', type=str, nargs='+', help='Prompts to analyze')
    parser.add_argument('--prompts-file', type=str, help='File containing prompts (one per line)')
    parser.add_argument('--output', type=str, help='Output file for results')
    parser.add_argument('--compare', action='store_true', help='Compare routing patterns across prompts')
    
    args = parser.parse_args()
    
    # Get prompts
    prompts = []
    if args.prompts:
        prompts.extend(args.prompts)
    if args.prompts_file:
        try:
            with open(args.prompts_file, 'r') as f:
                prompts.extend([line.strip() for line in f if line.strip()])
        except FileNotFoundError:
            print(f"Error: File {args.prompts_file} not found")
            return 1
    
    if not prompts:
        print("Error: No prompts provided. Use --prompts or --prompts-file")
        return 1
    
    # Build configuration
    config_kwargs = {}
    if args.model:
        config_kwargs['model_name'] = args.model
    if args.device:
        config_kwargs['device'] = args.device
    if args.load_in_4bit:
        config_kwargs['load_in_4bit'] = True
    
    try:
        config = load_model_config(preset=args.preset, **config_kwargs)
        
        print(f"Loading model: {config.model_name}")
        wrapper = MixtralWrapper(config)
        
        analyzer = ExpertUsageAnalyzer(num_experts=wrapper.client.num_experts)
        
        print(f"Analyzing {len(prompts)} prompts...")
        results, comparison = analyze_prompts(prompts, wrapper, analyzer)
        
        # Print summary
        print("\n=== Analysis Summary ===")
        for i, result in enumerate(results):
            print(f"\nPrompt {i+1}: {result['prompt'][:100]}...")
            print(f"Response: {result['response'][:100]}...")
            
            if result['expert_analysis']:
                analysis = result['expert_analysis']
                print(f"Experts used: {analysis['total_usage']} total")
                print(f"Most used expert: #{analysis['most_used_expert'][0]} ({analysis['most_used_expert'][1]} times)")
                print(f"Load balance score: {analysis['load_balance_score']:.3f}")
                print(f"Analysis: {analysis['analysis']}")
        
        # Print comparison if requested
        if args.compare and comparison:
            print("\n=== Pattern Comparison ===")
            comps = comparison['comparisons']
            print(f"Average correlation: {comps['avg_correlation']:.3f}")
            print(f"Most balanced: {comps['most_balanced']}")
            print(f"Least balanced: {comps['least_balanced']}")
            
            if comps['correlations']:
                print("\nPairwise correlations:")
                for corr in comps['correlations']:
                    print(f"  {corr['patterns'][0]} vs {corr['patterns'][1]}: {corr['correlation']:.3f}")
        
        # Save results if requested
        if args.output:
            output_data = {
                'config': {
                    'model_name': config.model_name,
                    'num_experts': wrapper.client.num_experts,
                    'experts_per_token': wrapper.client.experts_per_token
                },
                'results': results,
                'comparison': comparison
            }
            
            def json_serializer(obj):
                if hasattr(obj, '__dict__'):
                    return obj.__dict__
                return str(obj)
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=json_serializer)
            
            print(f"\nResults saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 