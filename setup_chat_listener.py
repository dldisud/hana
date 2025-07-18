import os
import sys
from pathlib import Path
import time
import threading

# 현재 디렉토리를 파이썬 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 전역 변수로 CHZZK_AVAILABLE과 YOUTUBE_AVAILABLE 선언
CHZZK_AVAILABLE = False
YOUTUBE_AVAILABLE = False

# 치지직 채팅 리스너 가져오기 시도
try:
    from chzzk_chat_listener import ChzzkChatListener
    CHZZK_AVAILABLE = True
except ImportError:
    CHZZK_AVAILABLE = False

# 유튜브 채팅 리스너 가져오기 시도
try:
    from youtube_chat_listener import YoutubeChatListener
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

def setup_chat_listener(channel_id, conversation_handler=None, cookies_path=None, platform="youtube", api_key=None):
    """채팅 리스너 설정
    
    Args:
        channel_id (str): 채널 ID 또는 비디오 ID
        conversation_handler (ConversationHandler, optional): 대화 처리 객체
        cookies_path (str, optional): 사용되지 않음 (호환성 유지용)
        platform (str, optional): 플랫폼 선택 ("youtube" 또는 "chzzk")
        api_key (str, optional): API 키 (유튜브 API용)
        
    Returns:
        ChatListener: 채팅 리스너 객체
    """
    global CHZZK_AVAILABLE, YOUTUBE_AVAILABLE
    
    # 유튜브 플랫폼 선택 시
    if platform.lower() == "youtube" and YOUTUBE_AVAILABLE:
        try:
            print(f"유튜브 비디오 ID {channel_id}의 채팅 리스너를 설정합니다...")
            chat_listener = YoutubeChatListener(channel_id, api_key)
            chat_listener.start()
            
            if conversation_handler:
                # 콜백 추가: 유튜브 채팅 메시지를 ConversationHandler로 전달
                def chat_callback(chat_data):
                    chat_data["is_donation"] = False
                    conversation_handler.process_input(chat_data)
                
                def donation_callback(donation_data):
                    donation_data["is_donation"] = True
                    conversation_handler.process_input(donation_data)
                
                chat_listener.add_callback(chat_callback)
                if hasattr(chat_listener, 'add_donation_callback'):
                    chat_listener.add_donation_callback(donation_callback)
            
            print(f"유튜브 비디오 ID {channel_id}의 채팅 리스너가 성공적으로 설정되었습니다.")
            return chat_listener
            
        except Exception as e:
            print(f"유튜브 채팅 리스너 설정 중 오류 발생: {e}")
            print("기본 채팅 리스너를 사용합니다.")
            YOUTUBE_AVAILABLE = False
    
    # 치지직 플랫폼 선택 시
    elif platform.lower() == "chzzk" and CHZZK_AVAILABLE:
        try:
            print(f"치지직 채널 ID {channel_id}의 채팅 리스너를 설정합니다...")
            chat_listener = ChzzkChatListener(channel_id)
            chat_listener.start()
            
            if conversation_handler:
                # 콜백 추가: 치지직 채팅 메시지를 ConversationHandler로 전달
                def chat_callback(chat_data):
                    chat_data["is_donation"] = False
                    conversation_handler.process_input(chat_data)
                
                def donation_callback(donation_data):
                    donation_data["is_donation"] = True
                    conversation_handler.process_input(donation_data)
                
                chat_listener.add_callback(chat_callback)
                if hasattr(chat_listener, 'add_donation_callback'):
                    chat_listener.add_donation_callback(donation_callback)
            
            print(f"치지직 채널 ID {channel_id}의 채팅 리스너가 성공적으로 설정되었습니다.")
            return chat_listener
            
        except Exception as e:
            print(f"치지직 채팅 리스너 설정 중 오류 발생: {e}")
            print("기본 채팅 리스너를 사용합니다.")
            CHZZK_AVAILABLE = False
    
    # 기본 채팅 리스너 사용
    print(f"채널 ID {channel_id}의 채팅을 수신하기 위한 기본 리스너를 설정합니다...")
    
    class ChatListener:
        def __init__(self, channel_id, conversation_handler=None):
            self.channel_id = channel_id
            self.running = True
            self.conversation_handler = conversation_handler
            self.callbacks = []
            self.donation_callbacks = []
        
        def add_callback(self, callback):
            self.callbacks.append(callback)
        
        def add_donation_callback(self, callback):
            print("기본 채팅 리스너는 도네이션 콜백을 지원하지 않습니다.")
            self.donation_callbacks.append(callback)
        
        def start(self):
            import threading
            threading.Thread(target=self._listen, daemon=True).start()
        
        def _listen(self):
            print("실제 채팅 API 연결 대기 중...")
            while self.running:
                time.sleep(1)
        
        def process_user_input(self, username, message):
            if not self.running:
                return
            chat_data = {
                "username": username,
                "message": message,
                "timestamp": time.time(),
                "platform": "manual",
                "is_donation": False
            }
            for callback in self.callbacks:
                callback(chat_data)
        
        def process_speech_input(self, message):
            """음성 입력 처리"""
            chat_data = {
                "username": "User",
                "message": message,
                "timestamp": time.time(),
                "platform": "speech",
                "is_donation": False
            }
            response = None
            if self.conversation_handler:
                response = self.conversation_handler.process_input(chat_data)
            else:
                for callback in self.callbacks:
                    response = callback(chat_data)
            return response
        
        def send_message(self, message):
            print(f"기본 채팅 리스너는 메시지 전송을 지원하지 않습니다: {message}")
            return False
        
        def stop(self):
            self.running = False
    
    chat_listener = ChatListener(channel_id, conversation_handler)
    chat_listener.start()
    return chat_listener
