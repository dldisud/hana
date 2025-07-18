import json
import threading
import time
import pytchat
import os

class YoutubeChatListener:
    def __init__(self, video_id, api_key=None):
        """
        유튜브 채팅 리스너 초기화
        
        Args:
            video_id (str): 유튜브 비디오 ID
            api_key (str, optional): 유튜브 API 키 (현재 pytchat에서는 필요하지 않음)
        """
        self.video_id = video_id
        self.api_key = api_key
        self.running = True
        self.callbacks = []
        self.donation_callbacks = []
        self.subscription_callbacks = []
        self.chat = None
        
    def add_callback(self, callback):
        """채팅 메시지가 도착했을 때 호출할 콜백 함수 추가"""
        self.callbacks.append(callback)
    
    def add_donation_callback(self, callback):
        """도네이션 메시지(슈퍼챗)가 도착했을 때 호출할 콜백 함수 추가"""
        self.donation_callbacks.append(callback)
        
    def add_subscription_callback(self, callback):
        """멤버십 메시지가 도착했을 때 호출할 콜백 함수 추가"""
        self.subscription_callbacks.append(callback)
    
    def start(self):
        """채팅 메시지 수신 시작"""
        print(f"비디오 ID {self.video_id}의 유튜브 채팅을 수신하기 위한 리스너를 설정합니다...")
        
        try:
            # pytchat 인스턴스 생성
            self.chat = pytchat.create(video_id=self.video_id)
            
            # 메시지 처리 스레드 시작
            threading.Thread(target=self._process_messages, daemon=True).start()
            
            print("유튜브 채팅 연결 성공")
            return True
        except Exception as e:
            print(f"유튜브 채팅 연결 실패: {e}")
            return False
    
    def _process_messages(self):
        """pytchat에서 메시지를 가져와 처리"""
        print(f"채팅 처리 시작: 비디오 ID {self.video_id}")
        while self.running and self.chat.is_alive():
            try:
                # 채팅 데이터 가져오기
                chat_data = self.chat.get()
                print(f"채팅 데이터 수신: {len(chat_data.items)} 개의 메시지")
                
                # 각 채팅 아이템 처리
                for item in chat_data.items:
                    print(f"채팅 메시지: {item.author.name} - {item.message}")
                    if item.type == "superChat" or item.type == "superSticker":
                        self._handle_donation(item)
                    elif item.type == "newSponsor":
                        self._handle_subscription(item)
                    else:  # "textMessage"
                        self._handle_chat(item)
                
                # 잠시 대기
                time.sleep(0.1)
            except Exception as e:
                print(f"메시지 처리 중 오류 발생: {e}")
                if not self.running:
                    break
                time.sleep(1)  # 오류 발생 시 잠시 대기 후 재시도
                
    def _handle_chat(self, item):
        """채팅 메시지 처리"""
        # 채팅 데이터를 hana.py에서 사용하는 형식으로 변환
        transformed_data = {
            "username": item.author.name,
            "message": item.message,
            "timestamp": item.timestamp / 1000,  # 밀리초를 초로 변환
            "is_mod": item.author.isChatModerator,
            "platform": "youtube",
            "is_donation": False
        }
        
        # 콜백 함수들을 호출하여 메시지 처리
        for callback in self.callbacks:
            callback(transformed_data)
    
    def _handle_donation(self, item):
        """도네이션(슈퍼챗) 메시지 처리"""
        # 도네이션 데이터를 hana.py에서 사용하는 형식으로 변환
        transformed_data = {
            "username": item.author.name,
            "message": item.message,
            "timestamp": item.timestamp / 1000,  # 밀리초를 초로 변환
            "amount": item.amountValue,
            "currency": item.currency,
            "is_mod": item.author.isChatModerator,
            "platform": "youtube",
            "is_donation": True
        }
        
        # 도네이션 콜백 함수들을 호출하여 메시지 처리
        for callback in self.donation_callbacks:
            callback(transformed_data)
            
    def _handle_subscription(self, item):
        """멤버십 메시지 처리"""
        # 구독 데이터를 hana.py에서 사용하는 형식으로 변환
        transformed_data = {
            "username": item.author.name,
            "message": item.message,
            "timestamp": item.timestamp / 1000,  # 밀리초를 초로 변환
            "is_mod": item.author.isChatModerator,
            "platform": "youtube"
        }
        
        # 구독 콜백 함수들을 호출하여 메시지 처리
        for callback in self.subscription_callbacks:
            callback(transformed_data)
    
    def process_user_input(self, username, message):
        """사용자 입력 처리 (직접 호출용)"""
        if not self.running:
            return
            
        chat_data = {
            "username": username,
            "message": message,
            "timestamp": time.time(),
            "platform": "manual",
            "is_donation": False
        }
        
        # 콜백 함수들을 호출하여 메시지 처리
        for callback in self.callbacks:
            callback(chat_data)
    
    def process_speech_input(self, message):
        """음성 입력 처리 (직접 호출용)"""
        if not self.running:
            return
            
        chat_data = {
            "username": "User",
            "message": message,
            "timestamp": time.time(),
            "platform": "speech",
            "is_donation": False
        }
        
        # 콜백 함수들을 호출하여 메시지 처리
        response = None
        for callback in self.callbacks:
            response = callback(chat_data)
        return response
    
    def send_message(self, message):
        """채팅 메시지 전송 (현재 지원되지 않음)"""
        print(f"메시지 전송 기능은 현재 지원되지 않습니다: {message}")
        return False
    
    def stop(self):
        """채팅 메시지 수신 중지"""
        self.running = False
        if self.chat:
            try:
                # pytchat에는 명시적인 종료 메서드가 없으므로 running 플래그만 변경
                pass
            except:
                pass
