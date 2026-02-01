#!/usr/bin/env python3
"""
Minimal test script to check if the basic imports and CUDA work
"""
import sys
print(f"Python version: {sys.version}")

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")
        
        # Test basic CUDA operations
        x = torch.randn(2, 2)
        y = x.cuda()
        print("Basic CUDA tensor creation: OK")
        
        del x, y
        torch.cuda.empty_cache()
        
except Exception as e:
    print(f"Error with PyTorch/CUDA: {e}")

try:
    from qwen_asr import Qwen3ASRModel
    print("qwen_asr import: OK")
except Exception as e:
    print(f"Error importing qwen_asr: {e}")

print("Basic checks complete.")