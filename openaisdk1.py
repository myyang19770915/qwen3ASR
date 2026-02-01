import httpx
from openai import OpenAI
import json

# Initialize client
client = OpenAI(
    base_url="http://localhost:8006/v1",
    api_key="EMPTY"
)

def stream_transcription_openai():
    """使用 OpenAI SDK 進行轉錄 (移除不支持的參數)"""
    audio_url = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav"
    audio_file = httpx.get(audio_url).content

    # 使用基本轉錄 (移除不支持的參數)
    try:
        transcription = client.audio.transcriptions.create(
            model="Qwen/Qwen3-ASR-1.7B",
            file=audio_file,
            # response_format="verbose_json",  # 不支持，移除
            # timestamp_granularities=["word"]  # 不支持，移除
        )
        
        print("📝 轉錄結果:")
        print(f"文本: {transcription.text}")
        
        # 模擬流式效果 - 逐詞輸出
        print("\n🎵 模擬流式輸出:")
        words = transcription.text.split()
        current_text = ""
        
        import time
        for word in words:
            current_text += word + " "
            print(f"\r{current_text.strip()}", end="", flush=True)
            time.sleep(0.2)  # 模擬實時效果
        
        print()  # 換行
        return transcription.text
                
    except Exception as e:
        print(f"❌ OpenAI SDK 轉錄失敗: {e}")
        return None

def stream_transcription_direct():
    """直接調用服務器 API (移除 sseclient 依賴)"""
    import requests
    
    audio_url = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav"
    audio_data = httpx.get(audio_url).content
    
    # 嘗試不同的 API 端點
    endpoints = [
        "http://localhost:8006/v1/audio/transcriptions",
        "http://localhost:8006/transcribe",
        "http://localhost:8006/api/transcribe"
    ]
    
    for endpoint in endpoints:
        print(f"🔍 嘗試端點: {endpoint}")
        
        try:
            # 準備請求數據
            files = {
                'file': ('audio.wav', audio_data, 'audio/wav')
            }
            
            data = {
                'model': 'Qwen/Qwen3-ASR-1.7B',
            }
            
            # 嘗試標準請求
            response = requests.post(endpoint, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'text' in result:
                        print(f"✅ 轉錄成功: {result['text']}")
                        return result['text']
                    else:
                        print(f"📝 轉錄結果: {result}")
                        return str(result)
                except json.JSONDecodeError:
                    # 純文本回應
                    text_result = response.text
                    print(f"📝 轉錄結果: {text_result}")
                    return text_result
            else:
                print(f"❌ 端點回應錯誤: {response.status_code}")
                print(f"錯誤內容: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 請求端點 {endpoint} 失敗: {e}")
            continue
    
    print("❌ 所有端點都不可用")
    return None

def stream_transcription_websocket():
    """WebSocket 轉錄 (簡化版本)"""
    print("ℹ️ WebSocket 流式轉錄需要服務器支持 WebSocket 端點")
    print("如果服務器支持，可以實現真正的實時轉錄")
    
    # 這裡提供 WebSocket 的概念性實現
    websocket_example = """
    WebSocket 實現示例：
    1. 連接 ws://localhost:8006/ws/transcribe
    2. 發送配置: {"model": "Qwen/Qwen3-ASR-1.7B"}
    3. 分塊發送音頻數據
    4. 接收實時轉錄結果
    """
    print(websocket_example)
    
    # 如果需要實際實現，請安裝: pip install websockets
    return "WebSocket 示例完成"

if __name__ == "__main__":
    print("🎵 Qwen3 ASR 流式轉錄測試\n")
    
    print("1️⃣ 嘗試 OpenAI SDK 詳細輸出...")
    stream_transcription_openai()
    
    print("\n" + "="*50 + "\n")
    
    print("2️⃣ 嘗試直接 HTTP 流式 API...")
    stream_transcription_direct()
    
    print("\n" + "="*50 + "\n")
    
    print("3️⃣ 嘗試 WebSocket 流式轉錄...")
    stream_transcription_websocket()
