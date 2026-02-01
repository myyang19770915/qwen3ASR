#!/usr/bin/env python3
"""
簡化的 Qwen3 ASR 客戶端 - 無額外依賴
"""
import httpx
import json
import time
from openai import OpenAI

def main():
    # 初始化 OpenAI 客戶端
    client = OpenAI(
        base_url="http://localhost:8006/v1",
        api_key="EMPTY"
    )
    
    # 測試音頻
    test_audios = [
        {
            "name": "英文音頻",
            "url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav"
        },
        {
            "name": "中文音頻", 
            "url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_zh.wav"
        }
    ]
    
    for i, audio_info in enumerate(test_audios, 1):
        print(f"\n{'='*60}")
        print(f"🎵 測試 {i}: {audio_info['name']}")
        print('='*60)
        
        try:
            # 下載音頻數據
            print("📥 下載音頻文件...")
            audio_data = httpx.get(audio_info['url']).content
            print(f"✅ 音頻文件大小: {len(audio_data)} bytes")
            
            # 使用 OpenAI SDK 進行轉錄
            print("🎤 開始轉錄...")
            start_time = time.time()
            
            transcription = client.audio.transcriptions.create(
                model="Qwen/Qwen3-ASR-1.7B",
                file=audio_data,
            )
            
            end_time = time.time()
            
            print("📝 轉錄完成!")
            print(f"⏱️ 耗時: {end_time - start_time:.2f} 秒")
            
            # 模擬流式輸出效果
            print("\n🎬 模擬實時流式輸出:")
            words = transcription.text.split()
            current_text = ""
            
            for word in words:
                current_text += word + " "
                print(f"\r📺 {current_text.strip()}", end="", flush=True)
                time.sleep(0.15)  # 調整速度
            
            print(f"\n\n✅ 最終結果: {transcription.text}")
            
        except Exception as e:
            print(f"❌ 轉錄失敗: {e}")
        
        # 分隔線
        if i < len(test_audios):
            print("\n" + "-"*40)
            print("⏳ 等待 2 秒後進行下一個測試...")
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("🎉 測試完成!")
    print('='*60)

if __name__ == "__main__":
    main()