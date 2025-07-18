import time
import threading

class ConversationHandler:
    def __init__(self, tts, chat):
        """대화 처리 핸들러 초기화
        
        Args:
            tts: 음성 합성 객체
            chat: 챗봇 객체
        """
        self.tts = tts
        self.chat = chat
        self.last_response_time = 0
        self.cooldown = 5  # 응답 간 최소 시간 간격 (초)
        self.is_processing = False
        self.processing_lock = threading.Lock()
        self.is_muted = False  # 음소거 상태 추가
        
    def process_input(self, chat_data):
        """채팅 입력 처리
        
        Args:
            chat_data: 채팅 데이터 (딕셔너리)
            
        Returns:
            str: AI 응답 텍스트
        """
        # 이미 처리 중이면 무시
        if self.is_processing:
            return None
            
        # 쿨다운 체크
        current_time = time.time()
        if current_time - self.last_response_time < self.cooldown:
            return None
            
        # 처리 시작
        with self.processing_lock:
            self.is_processing = True
            
            try:
                # 채팅 데이터 추출
                username = chat_data.get("username", "Unknown")
                message = chat_data.get("message", "")
                is_donation = chat_data.get("is_donation", False)
                platform = chat_data.get("platform", "unknown")
                
                # 도네이션 여부에 따라 프롬프트 구성
                if is_donation:
                    amount = chat_data.get("amount", "")
                    prompt = f"{username}님이 {amount} 후원하며: {message}"
                else:
                    prompt = f"{username}: {message}"
                
                # 챗봇에 메시지 전송
                response = self.chat.send_message(prompt)
                ai_response = response.text
                
                # 감정 추출 (간단한 키워드 기반)
                emotion = self._get_emotion_from_text(message)
                
                # 음성 합성 및 재생 (음소거 상태가 아닐 때만)
                if not self.is_muted:
                    audio_path = self.tts.synthesize_with_emotion(ai_response, emotion=emotion)
                    if audio_path:
                        self.tts.play_audio(audio_path)
                
                # 마지막 응답 시간 업데이트
                self.last_response_time = time.time()
                
                # 처리 완료
                self.is_processing = False
                
                return ai_response
                
            except Exception as e:
                print(f"대화 처리 중 오류 발생: {str(e)}")
                self.is_processing = False
                return None
    
    def _get_emotion_from_text(self, text):
        """텍스트에서 감정 추출 (간단한 키워드 기반)"""
        happy_keywords = ["좋아", "행복", "신나", "재미", "웃"]
        sad_keywords = ["슬퍼", "우울", "힘들", "아파", "싫어"]
        angry_keywords = ["화나", "짜증", "열받", "미쳐", "죽"]
        excited_keywords = ["대박", "와우", "멋져", "최고", "사랑"]
        
        text = text.lower()
        
        for word in happy_keywords:
            if word in text:
                return "happy"
        for word in sad_keywords:
            if word in text:
                return "sad"
        for word in angry_keywords:
            if word in text:
                return "angry"
        for word in excited_keywords:
            if word in text:
                return "excited"
                
        return "neutral"
    
    def set_mute(self, mute_state):
        """음소거 상태 설정
        
        Args:
            mute_state (bool): 음소거 상태 (True: 음소거, False: 음소거 해제)
        """
        self.is_muted = mute_state
