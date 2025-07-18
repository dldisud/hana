import json
import threading
import time
import subprocess
import os

class ChzzkChatListener:
    def __init__(self, channel_id, cookies_path=None):
        """
        치지직 채팅 리스너 초기화
        
        Args:
            channel_id (str): 치지직 채널 ID
            cookies_path (str, optional): 사용되지 않음 (호환성 유지용)
        """
        self.channel_id = channel_id
        self.running = True
        self.callbacks = []
        self.donation_callbacks = []
        self.subscription_callbacks = []
        self.process = None
        
        # 현재 스크립트 경로 확인
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.bridge_script = os.path.join(self.script_dir, "chzzk_bridge.js")
        
    def add_callback(self, callback):
        """채팅 메시지가 도착했을 때 호출할 콜백 함수 추가"""
        self.callbacks.append(callback)
    
    def add_donation_callback(self, callback):
        """도네이션 메시지가 도착했을 때 호출할 콜백 함수 추가"""
        self.donation_callbacks.append(callback)
        
    def add_subscription_callback(self, callback):
        """구독 메시지가 도착했을 때 호출할 콜백 함수 추가"""
        self.subscription_callbacks.append(callback)
    
    def start(self):
        """채팅 메시지 수신 시작"""
        print(f"채널 ID {self.channel_id}의 치지직 채팅을 수신하기 위한 리스너를 설정합니다...")
        
        # Node.js 브릿지 스크립트 실행
        try:
            self.process = subprocess.Popen(
                ["node", self.bridge_script, self.channel_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # UTF-8 인코딩 명시
                errors='replace',  # 디코딩 실패 시 대체 문자 사용
                bufsize=1
            )
            
            # 메시지 처리 스레드 시작
            threading.Thread(target=self._process_messages, daemon=True).start()
            
            # 에러 출력 스레드 시작
            threading.Thread(target=self._process_errors, daemon=True).start()
            
            print("치지직 채팅 연결 성공")
            return True
        except Exception as e:
            print(f"치지직 채팅 연결 실패: {e}")
            return False
    
    def _process_messages(self):
        """Node.js 브릿지 스크립트의 출력을 처리"""
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline().strip()
                if not line:
                    continue
                    
                data = json.loads(line)
                message_type = data.get("type", "")
                
                if message_type == "chat":
                    self._handle_chat(data)
                elif message_type == "donation":
                    self._handle_donation(data)
                elif message_type == "subscription":
                    self._handle_subscription(data)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"메시지 처리 중 오류 발생: {e}")
                
    def _process_errors(self):
        """Node.js 브릿지 스크립트의 에러 출력을 처리"""
        while self.running and self.process and self.process.poll() is None:
            line = self.process.stderr.readline().strip()
            if line:
                print(f"브릿지 스크립트: {line}")
    
    def _handle_chat(self, data):
        """채팅 메시지 처리"""
        # 채팅 데이터를 hana.py에서 사용하는 형식으로 변환
        transformed_data = {
            "username": data["username"],
            "message": data["message"],
            "timestamp": data["timestamp"],
            "is_mod": "mod" in data.get("badges", []),
            "platform": "chzzk",
            "is_donation": False
        }
        
        # 콜백 함수들을 호출하여 메시지 처리
        for callback in self.callbacks:
            callback(transformed_data)
    
    def _handle_donation(self, data):
        """도네이션 메시지 처리"""
        # 도네이션 데이터를 hana.py에서 사용하는 형식으로 변환
        transformed_data = {
            "username": data["username"],
            "message": data["message"],
            "timestamp": data["timestamp"],
            "amount": data["amount"],
            "is_mod": "mod" in data.get("badges", []),
            "platform": "chzzk",
            "is_donation": True
        }
        
        # 도네이션 콜백 함수들을 호출하여 메시지 처리
        for callback in self.donation_callbacks:
            callback(transformed_data)
            
    def _handle_subscription(self, data):
        """구독 메시지 처리"""
        # 구독 데이터를 hana.py에서 사용하는 형식으로 변환
        transformed_data = {
            "username": data["username"],
            "message": data["message"],
            "timestamp": data["timestamp"],
            "month": data["month"],
            "tierName": data["tierName"],
            "tierNo": data["tierNo"],
            "is_mod": "mod" in data.get("badges", []),
            "platform": "chzzk"
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
        for callback in self.callbacks:
            callback(chat_data)
    
    def send_message(self, message):
        """채팅 메시지 전송 (현재 지원되지 않음)"""
        print(f"메시지 전송 기능은 현재 지원되지 않습니다: {message}")
        return False
    
    def stop(self):
        """채팅 메시지 수신 중지"""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()