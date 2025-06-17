"""Mixtral model wrapper with enhanced MoE analysis capabilities."""

from typing import Dict, List, Optional, Any, Tuple
import torch
from ..core.mixtral_client import MixtralClient, MixtralResponse
from ..core.router_analyzer import RouterAnalyzer
from ..core.config import MixtralConfig


class MixtralWrapper:
    """Simplified wrapper for Mixtral models with built-in MoE analysis."""
    
    def __init__(self, config: MixtralConfig):
        """
        Initialize Mixtral wrapper.
        
        Args:
            config: Mixtral configuration object
        """
        self.config = config
        self.client = MixtralClient(
            model_name=config.model_name,
            device=config.device,
            torch_dtype=config.torch_dtype,
            load_in_8bit=config.load_in_8bit,
            load_in_4bit=config.load_in_4bit,
            device_map=config.device_map
        )
        
        self.analyzer = RouterAnalyzer(
            num_experts=self.client.num_experts,
            experts_per_token=self.client.experts_per_token
        )
        self.analyzer.set_tokenizer(self.client.tokenizer)
        
        # Store analysis history
        self.analysis_history = []
    
    def query(
        self, 
        prompt: str, 
        analyze_routing: bool = True,
        **generation_kwargs
    ) -> MixtralResponse:
        """
        Generate text with optional routing analysis.
        
        Args:
            prompt: Input prompt
            analyze_routing: Whether to analyze router decisions
            **generation_kwargs: Additional generation parameters
            
        Returns:
            MixtralResponse with text and routing information
        """
        # Merge config defaults with kwargs
        gen_params = {
            'max_new_tokens': self.config.max_new_tokens,
            'temperature': self.config.temperature,
            'top_p': self.config.top_p,
            'top_k': self.config.top_k,
            'do_sample': self.config.do_sample,
            'analyze_routing': analyze_routing,
        }
        gen_params.update(generation_kwargs)
        
        return self.client.generate(prompt, **gen_params)
    
    def analyze_response(self, response: MixtralResponse) -> Optional[Dict[str, Any]]:
        """
        Analyze routing decisions from a response.
        
        Args:
            response: MixtralResponse object
            
        Returns:
            Analysis results or None if no routing data available
        """
        if not response.router_selections:
            return None
        
        analysis = self.analyzer.analyze_routing_decisions(
            response.router_selections,
            response.tokens
        )
        
        # Add to history
        self.analysis_history.append({
            'prompt_length': len(response.tokens),
            'analysis': analysis
        })
        
        return analysis
    
    def get_expert_usage_summary(self, response: MixtralResponse) -> str:
        """
        Get a human-readable summary of expert usage for a response.
        
        Args:
            response: MixtralResponse object
            
        Returns:
            Summary string
        """
        analysis = self.analyze_response(response)
        if not analysis:
            return "No routing analysis available."
        
        return self.analyzer.get_expert_usage_summary(analysis)
    
    def compare_prompts(
        self, 
        prompts: List[str], 
        **generation_kwargs
    ) -> Dict[str, Any]:
        """
        Compare expert usage patterns across multiple prompts.
        
        Args:
            prompts: List of prompts to compare
            **generation_kwargs: Generation parameters
            
        Returns:
            Comparison analysis
        """
        results = []
        analyses = []
        
        for i, prompt in enumerate(prompts):
            print(f"Processing prompt {i+1}/{len(prompts)}: {prompt[:50]}...")
            response = self.query(prompt, analyze_routing=True, **generation_kwargs)
            analysis = self.analyze_response(response)
            
            results.append({
                'prompt': prompt,
                'response': response.text,
                'analysis': analysis
            })
            
            if analysis:
                analyses.append(analysis)
        
        # Compare patterns if we have analyses
        comparison = None
        if len(analyses) >= 2:
            comparison = {
                'num_prompts': len(prompts),
                'analyses': analyses,
                'differences': self._compare_analyses(analyses)
            }
        
        return {
            'individual_results': results,
            'comparison': comparison
        }
    
    def _compare_analyses(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare multiple analysis results."""
        if len(analyses) < 2:
            return {}
        
        # Compare expert usage across analyses
        usage_patterns = []
        for analysis in analyses:
            global_stats = analysis['global_statistics']
            usage = [global_stats['global_expert_usage'].get(i, 0) 
                    for i in range(self.client.num_experts)]
            usage_patterns.append(usage)
        
        # Calculate correlations between patterns
        import numpy as np
        correlations = []
        for i in range(len(usage_patterns)):
            for j in range(i + 1, len(usage_patterns)):
                corr = np.corrcoef(usage_patterns[i], usage_patterns[j])[0, 1]
                correlations.append(corr)
        
        return {
            'usage_patterns': usage_patterns,
            'correlations': correlations,
            'avg_correlation': np.mean(correlations) if correlations else 0.0,
            'pattern_similarity': 'High' if np.mean(correlations) > 0.8 else 'Low'
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        info = self.client.get_model_info()
        info.update({
            'config': self.config,
            'analysis_history_count': len(self.analysis_history)
        })
        return info
    
    def reset_analysis_history(self):
        """Clear the analysis history."""
        self.analysis_history.clear()
    
    def export_analysis_history(self, filepath: str):
        """
        Export analysis history to file.
        
        Args:
            filepath: Path to save the analysis history
        """
        import json
        
        def convert_for_json(obj):
            if isinstance(obj, torch.Tensor):
                return obj.tolist()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return obj
        
        with open(filepath, 'w') as f:
            json.dump(self.analysis_history, f, indent=2, default=convert_for_json)
        
        print(f"Analysis history exported to {filepath}")
    
    def batch_analyze(
        self, 
        prompts: List[str], 
        batch_size: int = 5,
        **generation_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple prompts in batches.
        
        Args:
            prompts: List of prompts to analyze
            batch_size: Number of prompts to process at once
            **generation_kwargs: Generation parameters
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(prompts) + batch_size - 1)//batch_size}")
            
            for prompt in batch:
                response = self.query(prompt, analyze_routing=True, **generation_kwargs)
                analysis = self.analyze_response(response)
                
                results.append({
                    'prompt': prompt,
                    'response_text': response.text,
                    'analysis': analysis,
                    'expert_usage': response.expert_usage
                })
        
        return results 