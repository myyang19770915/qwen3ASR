import torch
import torch.distributed as dist
from qwen_asr import Qwen3ASRModel
import atexit
import gc
import os

# 設置環境變數以提高穩定性
os.environ['PYTORCH_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

def cleanup_distributed():
    """Clean up distributed processes on exit"""
    if dist.is_initialized():
        dist.destroy_process_group()

if __name__ == '__main__':
    # Register cleanup function to run on exit
    atexit.register(cleanup_distributed)
    
    # 清理GPU緩存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()
    
    try:
        model = Qwen3ASRModel.LLM(
            model="Qwen/Qwen3-ASR-1.7B",
            gpu_memory_utilization=0.5,  # 降低到0.5，更保守的記憶體使用
            max_inference_batch_size=2,  # 降低到1，減少批次大小
            max_new_tokens=2048,  # 降低到2048，減少記憶體需求
            forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
            forced_aligner_kwargs=dict(
                dtype=torch.bfloat16,
                device_map="cuda:0",
                attn_implementation="flash_attention_2",  # 暫時移除flash attention
            ),
        )
        print("✅ 模型載入成功!")
        
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        exit(1)

    try:
        results = model.transcribe(
            audio=[
            "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_zh.wav",
            "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav",
            ],
            language=["Chinese", "English"], # can also be set to None for automatic language detection
            return_time_stamps=True,
        )

        for r in results:
            print(f"🎵 {r.language}: {r.text}")
            print(f"⏰ 時間戳: {r.time_stamps[0]}")
            
    except Exception as e:
        print(f"❌ 轉錄失敗: {e}")
        
    finally:
        # 清理資源
        if 'model' in locals():
            del model
        cleanup_distributed()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        print("🧹 資源清理完成")
