#!/usr/bin/env python3
"""Analyze Mixtral MoE routing patterns."""

import argparse
import sys
import json
from ..core.config import load_model_config, check_quantization_support
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
    parser.add_argument('--device', type=str, help='Device to use (cuda, cpu, auto)', choices=['cuda', 'cpu', 'auto'], default='auto')
    parser.add_argument('--load-in-4bit', action='store_true', help='Load in 4-bit precision (requires compatible bitsandbytes)')
    parser.add_argument('--load-in-8bit', action='store_true', help='Load in 8-bit precision (requires compatible bitsandbytes)')
    parser.add_argument('--prompts', type=str, nargs='+', help='Prompts to analyze')
    parser.add_argument('--prompts-file', type=str, help='File containing prompts (one per line)')
    parser.add_argument('--output', type=str, help='Output file for results')
    parser.add_argument('--compare', action='store_true', help='Compare routing patterns across prompts')
    parser.add_argument('--check-system', action='store_true', help='Check system capabilities for quantization')
    
    args = parser.parse_args()
    
    # Handle system check
    if args.check_system:
        import torch
        print("=== System Capabilities Check ===")
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        
        print("\nQuantization Support:")
        quant_support = check_quantization_support()
        print(f"  bitsandbytes available: {quant_support['bitsandbytes_available']}")
        if quant_support['error']:
            print(f"  Error: {quant_support['error']}")
            if quant_support['suggestion']:
                print(f"  Suggestion: {quant_support['suggestion']}")
        else:
            print(f"  CUDA support: {quant_support['cuda_support']}")
            print(f"  CPU support: {quant_support['cpu_support']}")
        
        print("\nRecommendations:")
        if not quant_support['bitsandbytes_available'] or quant_support['error']:
            print("  - Use full precision models (remove --load-in-4bit/--load-in-8bit)")
            print("  - For CUDA support: Need bitsandbytes compiled with CUDA")
            print("  - For CPU support: Need intel_extension_for_pytorch for Intel CPUs")
        else:
            print("  - Quantization should work on this system")
        
        return 0
    
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
    
    # Check quantization availability before setting flags
    quantization_requested = args.load_in_4bit or args.load_in_8bit
    if quantization_requested:
        print(f"Quantization requested: 4-bit={args.load_in_4bit}, 8-bit={args.load_in_8bit}")
        try:
            quant_support = check_quantization_support()
            print(f"Quantization check result: available={quant_support['bitsandbytes_available']}, error={quant_support['error']}")
            
            if not quant_support['bitsandbytes_available'] or quant_support['error']:
                print(f"Warning: Quantization requested but not available")
                print(f"  Reason: {quant_support['error']}")
                if quant_support['suggestion']:
                    print(f"  Suggestion: {quant_support['suggestion']}")
                print(f"  Continuing with full precision...")
                print(f"  (Use --check-system to see detailed capabilities)")
                # DO NOT set quantization flags - leave them out of config_kwargs
            else:
                print(f"Quantization is available, enabling it")
                if args.load_in_4bit:
                    config_kwargs['load_in_4bit'] = True
                if args.load_in_8bit:
                    config_kwargs['load_in_8bit'] = True
        except Exception as e:
            print(f"Error checking quantization support: {e}")
            print(f"Disabling quantization as a safety measure")
            # DO NOT set quantization flags
    else:
        print(f"No quantization requested")
    
    # Handle device detection
    import torch
    if args.device == 'auto':
        if torch.cuda.is_available():
            config_kwargs['device'] = 'cuda'
            print(f"Auto-detected CUDA device")
        else:
            config_kwargs['device'] = 'cpu'
            print(f"CUDA not available, using CPU")
    else:
        config_kwargs['device'] = args.device
        if args.device == 'cuda' and not torch.cuda.is_available():
            print(f"Warning: CUDA requested but not available, using CPU instead")
            config_kwargs['device'] = 'cpu'
    
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