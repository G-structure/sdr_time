"""Mixtral model client with router analysis capabilities."""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
from dataclasses import dataclass


def check_bitsandbytes_availability():
    """Check if bitsandbytes is available and supports the current system."""
    try:
        import bitsandbytes as bnb
        # Try to actually test bitsandbytes functionality by creating a simple quantized tensor
        import torch
        
        # Test if any backend is actually supported
        try:
            # This will fail if no supported backend is available
            from bitsandbytes.functional import quantize_4bit
            # Try to quantize a small tensor to test if it works
            test_tensor = torch.randn(10, 10)
            quantize_4bit(test_tensor)
            return True
        except Exception as e:
            print(f"Debug: bitsandbytes test failed: {e}")
            return False
            
    except ImportError:
        return False
    except Exception as e:
        # bitsandbytes is installed but might not support this system
        print(f"Warning: bitsandbytes is installed but not working: {e}")
        return False


@dataclass
class MixtralResponse:
    """Response from Mixtral model including router information."""
    text: str
    tokens: List[int]
    router_logits: Optional[List[torch.Tensor]] = None
    router_selections: Optional[List[Dict[str, Any]]] = None
    expert_usage: Optional[Dict[int, int]] = None


class MixtralClient:
    """High-level client for Mixtral MoE models with router analysis."""
    
    def __init__(
        self,
        model_name: str = "mistralai/Mixtral-8x7B-Instruct-v0.1",
        device: Optional[str] = None,
        torch_dtype: Optional[torch.dtype] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        device_map: Optional[Union[str, Dict]] = "auto"
    ):
        """
        Initialize Mixtral client.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to load model on 
            torch_dtype: Torch data type for model weights
            load_in_8bit: Whether to load model in 8-bit precision
            load_in_4bit: Whether to load model in 4-bit precision
            device_map: Device mapping for model layers
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.torch_dtype = torch_dtype or torch.float16
        
        print(f"Loading model: {model_name}")
        print(f"Device: {self.device}")
        print(f"Data type: {self.torch_dtype}")
        
        # Check bitsandbytes availability
        bnb_available = check_bitsandbytes_availability()
        print(f"Bitsandbytes availability check: {bnb_available}")
        
        if (load_in_8bit or load_in_4bit) and not bnb_available:
            print("Warning: Quantization requested but bitsandbytes is not available or compatible.")
            print("Falling back to full precision loading.")
            load_in_8bit = False
            load_in_4bit = False
        
        if (load_in_8bit or load_in_4bit):
            print(f"Quantization will be attempted: 8-bit={load_in_8bit}, 4-bit={load_in_4bit}")
        else:
            print("Loading in full precision (no quantization)")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model with appropriate configuration
        model_kwargs = {
            "torch_dtype": self.torch_dtype,
            "device_map": device_map,
            "trust_remote_code": True,
        }
        
        # Only add quantization if bitsandbytes is available
        if bnb_available:
            if load_in_8bit:
                model_kwargs["load_in_8bit"] = True
                print("Loading with 8-bit quantization")
            elif load_in_4bit:
                model_kwargs["load_in_4bit"] = True
                print("Loading with 4-bit quantization")
        
        # Load config first to enable router logits
        config = AutoConfig.from_pretrained(model_name)
        config.output_router_logits = True
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            config=config,
            **model_kwargs
        )
        
        print(f"Model loaded successfully")
        print(f"Model type: {type(self.model)}")
        print(f"Number of parameters: {self.model.num_parameters():,}")
        
        # Get model configuration info
        self.config = self.model.config
        self.num_experts = getattr(self.config, 'num_local_experts', 8)
        self.experts_per_token = getattr(self.config, 'num_experts_per_tok', 2)
        
        print(f"MoE Configuration:")
        print(f"  - Number of experts: {self.num_experts}")
        print(f"  - Experts per token: {self.experts_per_token}")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: Optional[int] = None,
        do_sample: bool = True,
        analyze_routing: bool = True
    ) -> MixtralResponse:
        """
        Generate text with optional router analysis.
        
        Args:
            prompt: Input text prompt
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p (nucleus) sampling parameter
            top_k: Top-k sampling parameter
            do_sample: Whether to use sampling or greedy decoding
            analyze_routing: Whether to analyze router decisions
            
        Returns:
            MixtralResponse containing generated text and routing information
        """
        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generation parameters
        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.eos_token_id,
            "output_router_logits": analyze_routing,
            "return_dict_in_generate": True,
        }
        
        if top_k is not None:
            generation_kwargs["top_k"] = top_k
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                **generation_kwargs
            )
        
        # Extract generated tokens
        generated_tokens = outputs.sequences[0]
        input_length = inputs.input_ids.shape[1]
        new_tokens = generated_tokens[input_length:]
        
        # Decode generated text
        generated_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        
        # Analyze routing if requested
        router_logits = None
        router_selections = None
        expert_usage = None
        
        if analyze_routing and hasattr(outputs, 'router_logits') and outputs.router_logits:
            router_logits = outputs.router_logits
            router_selections, expert_usage = self._analyze_routing(router_logits)
        
        return MixtralResponse(
            text=generated_text,
            tokens=new_tokens.tolist(),
            router_logits=router_logits,
            router_selections=router_selections,
            expert_usage=expert_usage
        )
    
    def forward_with_routing(
        self,
        input_text: str
    ) -> Tuple[torch.Tensor, List[torch.Tensor]]:
        """
        Forward pass with router logit extraction.
        
        Args:
            input_text: Input text to process
            
        Returns:
            Tuple of (logits, router_logits)
        """
        inputs = self.tokenizer(input_text, return_tensors="pt")
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs, output_router_logits=True)
        
        return outputs.logits, outputs.router_logits
    
    def _analyze_routing(
        self, 
        router_logits: List[torch.Tensor]
    ) -> Tuple[List[Dict[str, Any]], Dict[int, int]]:
        """
        Analyze router decisions from logits.
        
        Args:
            router_logits: List of router logit tensors for each layer
            
        Returns:
            Tuple of (routing_decisions, expert_usage_counts)
        """
        routing_decisions = []
        expert_usage = {i: 0 for i in range(self.num_experts)}
        
        for layer_idx, layer_router_logits in enumerate(router_logits):
            # router_logits shape: [batch_size, sequence_length, num_experts]
            batch_size, seq_len, num_experts = layer_router_logits.shape
            
            # Get top-k experts for each token
            top_experts_logits, top_experts_indices = torch.topk(
                layer_router_logits, 
                k=self.experts_per_token, 
                dim=-1
            )
            
            # Convert to probabilities
            top_experts_probs = torch.softmax(top_experts_logits, dim=-1)
            
            layer_decisions = []
            for batch_idx in range(batch_size):
                for token_idx in range(seq_len):
                    experts = top_experts_indices[batch_idx, token_idx].tolist()
                    probs = top_experts_probs[batch_idx, token_idx].tolist()
                    
                    decision = {
                        'layer': layer_idx,
                        'token_position': token_idx,
                        'selected_experts': experts,
                        'expert_probabilities': probs,
                        'raw_logits': layer_router_logits[batch_idx, token_idx].tolist()
                    }
                    layer_decisions.append(decision)
                    
                    # Update usage counts
                    for expert_id in experts:
                        expert_usage[expert_id] += 1
            
            routing_decisions.extend(layer_decisions)
        
        return routing_decisions, expert_usage
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'torch_dtype': str(self.torch_dtype),
            'num_parameters': self.model.num_parameters(),
            'num_experts': self.num_experts,
            'experts_per_token': self.experts_per_token,
            'vocab_size': self.config.vocab_size,
            'hidden_size': self.config.hidden_size,
            'num_hidden_layers': self.config.num_hidden_layers,
            'num_attention_heads': self.config.num_attention_heads,
        } 