#!/usr/bin/env python3
"""
Qwen3 ASR 客戶端測試程序
用於連接 vLLM 服務器進行語音識別
"""
import requests
import json

class ASRClient:
    def __init__(self, server_url="http://127.0.0.1:8006"):
        self.server_url = server_url
        self.session = requests.Session()
    
    def transcribe(self, audio_url, language="auto"):
        """
        發送語音識別請求
        """
        try:
            # 測試服務器是否可用
            response = self.session.get(f"{self.server_url}/health")
            if response.status_code == 200:
                print(f"✅ 服務器連接成功: {self.server_url}")
            
        except requests.exceptions.ConnectionError:
            print(f"❌ 無法連接到服務器: {self.server_url}")
            return None
        
        # 發送轉錄請求
        payload = {
            "audio": audio_url,
            "language": language,
            "return_timestamps": True
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/transcribe", 
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 請求失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 請求錯誤: {e}")
            return None

def main():
    # 嘗試不同的連接方式
    servers = [
        "http://127.0.0.1:8006",      # WSL 內部
        "http://localhost:8006",       # Windows 主機
        "http://172.20.88.124:8006"   # 網絡連接
    ]
    
    client = None
    for server_url in servers:
        print(f"🔍 嘗試連接: {server_url}")
        test_client = ASRClient(server_url)
        
        try:
            # 測試連接
            response = test_client.session.get(f"{server_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ 成功連接: {server_url}")
                client = test_client
                break
        except:
            print(f"❌ 連接失敗: {server_url}")
    
    if not client:
        print("❌ 所有服務器連接均失敗")
        return
    
    # 測試語音識別
    test_audio = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_zh.wav"
    print(f"\n🎤 開始轉錄音頻: {test_audio}")
    
    result = client.transcribe(test_audio, language="Chinese")
    if result:
        print(f"📝 轉錄結果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("❌ 轉錄失敗")

if __name__ == "__main__":
    main()