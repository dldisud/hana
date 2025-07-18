import pytchat
import time

# 유튜브 비디오 ID를 여기에 입력하세요
video_id = "CwwF70A6I5k"

print(f"비디오 ID {video_id}의 채팅을 가져오는 중...")
chat = pytchat.create(video_id=video_id)

print("채팅 모니터링 시작...")
while chat.is_alive():
    try:
        # 채팅 데이터 가져오기
        chat_data = chat.get()
        print(f"채팅 데이터 수신: {len(chat_data.items)} 개의 메시지")
        
        # 각 채팅 아이템 처리
        for item in chat_data.items:
            print(f"[{item.datetime}] {item.author.name}: {item.message}")
        
        # 잠시 대기
        time.sleep(3)
    except Exception as e:
        print(f"오류 발생: {e}")
        time.sleep(1)

print("채팅 모니터링 종료")
