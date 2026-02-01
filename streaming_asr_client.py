#!/usr/bin/env python3
"""
Qwen3 ASR 簡化流式轉錄客戶端
"""
import httpx
import json
import time
from openai import OpenAI

class StreamingASRClient:
    def __init__(self, base_url="http://localhost:8006"):
        self.base_url = base_url
        self.openai_client = OpenAI(
            base_url=f"{base_url}/v1",
            api_key="EMPTY"
        )
    
    def stream_with_chunks(self, audio_url, chunk_duration=2.0):
        """
        模擬實時流式轉錄 - 分塊處理音頻
        """
        print(f"🎤 開始流式轉錄: {audio_url}")
        print("📺 實時輸出 (模擬):")
        
        try:
            # 獲取音頻數據
            audio_data = httpx.get(audio_url).content
            
            # 使用 OpenAI SDK 獲取完整轉錄
            transcription = self.openai_client.audio.transcriptions.create(
                model="Qwen/Qwen3-ASR-1.7B",
                file=audio_data,
                response_format="verbose_json",
            )
            
            # 模擬流式輸出 - 逐詞顯示
            words = transcription.text.split()
            current_text = ""
            
            for i, word in enumerate(words):
                current_text += word + " "
                print(f"\r🎵 {current_text}", end="", flush=True)
                time.sleep(0.3)  # 模擬實時效果
            
            print(f"\n✅ 轉錄完成!")
            print(f"📝 完整文本: {transcription.text}")
            
            return transcription.text
            
        except Exception as e:
            print(f"❌ 流式轉錄失敗: {e}")
            return None
    
    def direct_stream(self, audio_url):
        """
        嘗試直接調用流式端點
        """
        import requests
        
        print(f"🎤 嘗試直接流式 API: {audio_url}")
        
        try:
            audio_data = httpx.get(audio_url).content
            
            # 嘗試不同的流式端點
            endpoints = [
                f"{self.base_url}/v1/audio/transcriptions",
                f"{self.base_url}/transcribe/stream",
                f"{self.base_url}/stream/transcribe"
            ]
            
            for endpoint in endpoints:
                print(f"🔍 嘗試端點: {endpoint}")
                
                files = {'file': ('audio.wav', audio_data, 'audio/wav')}
                data = {
                    'model': 'Qwen/Qwen3-ASR-1.7B',
                    'stream': 'true'
                }
                
                try:
                    response = requests.post(endpoint, files=files, data=data, stream=True, timeout=10)
                    
                    if response.status_code == 200:
                        print("📺 流式輸出:")
                        buffer = ""
                        
                        for line in response.iter_lines(decode_unicode=True):
                            if line:
                                if line.startswith('data: '):
                                    data_content = line[6:]
                                    if data_content != '[DONE]':
                                        try:
                                            chunk = json.loads(data_content)
                                            if 'text' in chunk:
                                                print(f"🎵 {chunk['text']}")
                                            elif 'delta' in chunk and 'content' in chunk['delta']:
                                                print(chunk['delta']['content'], end='', flush=True)
                                        except json.JSONDecodeError:
                                            print(data_content, end='', flush=True)
                                else:
                                    print(line, end='', flush=True)
                        
                        print("\n✅ 流式轉錄完成!")
                        return True
                        
                except requests.exceptions.RequestException as e:
                    print(f"❌ 端點 {endpoint} 失敗: {e}")
                    continue
            
            print("❌ 所有流式端點都不可用")
            return False
            
        except Exception as e:
            print(f"❌ 直接流式轉錄失敗: {e}")
            return False

def main():
    client = StreamingASRClient()
    
    # 測試音頻
    test_audios = [
        "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav",
        "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_zh.wav"
    ]
    
    for i, audio_url in enumerate(test_audios, 1):
        print(f"\n{'='*60}")
        print(f"測試 {i}: {audio_url.split('/')[-1]}")
        print('='*60)
        
        # 方法1: 模擬流式輸出
        print("\n🚀 方法1: 模擬實時流式輸出")
        client.stream_with_chunks(audio_url)
        
        print("\n" + "-"*40)
        
        # 方法2: 嘗試真實流式API
        print("\n🚀 方法2: 嘗試真實流式 API")
        success = client.direct_stream(audio_url)
        
        if not success:
            print("ℹ️ 流式 API 不可用，使用標準 API")
            try:
                transcription = client.openai_client.audio.transcriptions.create(
                    model="Qwen/Qwen3-ASR-1.7B",
                    file=httpx.get(audio_url).content,
                )
                print(f"📝 標準轉錄結果: {transcription.text}")
            except Exception as e:
                print(f"❌ 標準轉錄也失敗: {e}")
        
        if i < len(test_audios):
            print("\n⏳ 等待 2 秒後進行下一個測試...")
            time.sleep(2)

if __name__ == "__main__":
    main()