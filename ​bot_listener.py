import time
import requests
import os

# 이미 발급받아 두신 토큰과 정보를 여기에 입력하세요
TELEGRAM_BOT_TOKEN = "여기에_텔레그램_봇_토큰"
GITHUB_TOKEN = "여기에_아까_발급받은_깃허브_토큰"
GITHUB_REPO = "mingi201/shorts-automation"  # 본인의 정확한 깃허브 저장소 이름

def trigger_github_action():
    """GitHub Actions 워크플로우를 원격으로 강제 실행하는 함수"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/main.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {"ref": "main"}
    res = requests.post(url, headers=headers, json=data)
    return res.status_code == 204

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def main():
    print("🤖 텔레그램 숏츠 제어 봇이 대기 중입니다...")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35)
            data = res.json()
            
            if data.get("ok"):
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    text = message.get("text", "").strip()
                    chat_id = message.get("chat", {}).get("id")
                    
                    if text in ["/shorts", "/시작", "/제작"]:
                        send_msg(chat_id, "🚀 숏츠 영상 제작 명령이 접수되었습니다! GitHub 서버를 가동합니다...")
                        
                        success = trigger_github_action()
                        if success:
                            send_msg(chat_id, "✅ GitHub Actions 작동 성공! 1~2분 뒤 완성된 영상이 이곳으로 전송됩니다.")
                        else:
                            send_msg(chat_id, "❌ GitHub 트리거 실패. 토큰이나 저장소 이름을 확인해주세요.")
                            
        except Exception as e:
            print(f"Polling error: {e}")
        time.sleep(2)

if __name__ == "__main__":
    main()
