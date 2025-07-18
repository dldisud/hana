import numpy as np
import sounddevice as sd
import whisper
import queue
import threading
import torch
import time

class RealtimeSTT:
    def __init__(self, model_size="medium", language="ko", device="cuda"):
        print("Whisper 모델 로딩 중...")
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"사용 장치: {self.device}")
        self.model = whisper.load_model(model_size, device=self.device)
        self.language = language
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = False
        self.silence_threshold = 0.01
        self.silence_counter = 0
        self.max_silence = 30
        self.sample_rate = 16000
        self.block_size = 1600
        self.buffer = []
        self.min_speech_duration = 0.5
        self.is_speaking = False
        self.last_text = None  # 중복 방지를 위한 변수 추가
        print("Whisper 모델 로딩 완료")
    
    def start(self):
        """음성 인식 시작"""
        if self.running:
            return
        
        self.running = True
        
        # 오디오 레코딩 스레드 시작
        self.record_thread = threading.Thread(target=self._record_audio)
        self.record_thread.daemon = True
        self.record_thread.start()
        
        # 음성 처리 스레드 시작
        self.process_thread = threading.Thread(target=self._process_audio)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        print("실시간 음성 인식 시작")
    
    def stop(self):
        """음성 인식 중지"""
        self.running = False
        
        # 남은 오디오 처리
        if self.buffer:
            audio_data = np.concatenate(self.buffer)
            if len(audio_data) / self.sample_rate >= self.min_speech_duration:
                self._transcribe(audio_data)
        
        print("실시간 음성 인식 중지")
    
    def get_result(self):
        """인식 결과 가져오기"""
        if not self.result_queue.empty():
            return self.result_queue.get()
        return None
    
    def _record_audio(self):
        """마이크에서 오디오 녹음"""
        def audio_callback(indata, frames, time, status):
            """오디오 입력 콜백"""
            if not self.running:
                return
            
            # 모노로 변환
            audio_data = indata[:, 0].copy()
            self.audio_queue.put(audio_data)
        
        # 오디오 스트림 시작
        with sd.InputStream(callback=audio_callback, 
                           channels=1, 
                           samplerate=self.sample_rate,
                           blocksize=self.block_size):
            while self.running:
                time.sleep(0.1)
    
    def _process_audio(self):
        """오디오 처리 및 음성 감지 (최적화 버전)"""
        while self.running:
            if not self.audio_queue.empty():
                # 오디오 데이터 가져오기
                audio_data = self.audio_queue.get()
                
                # 볼륨 레벨 계산
                volume_level = np.abs(audio_data).mean()
                
                # 음성 감지
                if volume_level > self.silence_threshold:
                    # 음성 감지됨
                    if not self.is_speaking:
                        # 발화 시작
                        self.is_speaking = True
                        print("음성 감지 시작...")
                    
                    self.silence_counter = 0
                    self.buffer.append(audio_data)
                else:
                    # 무음 감지됨
                    if self.is_speaking and self.buffer:
                        # 무음 카운터 증가
                        self.silence_counter += 1
                        self.buffer.append(audio_data)  # 잠시 동안의 무음도 버퍼에 추가
                        
                        # 무음이 일정 기간 지속되면 즉시 처리
                        if self.silence_counter >= self.max_silence:
                            # 발화 종료 감지
                            self.is_speaking = False
                            
                            # 모든 오디오 데이터 결합
                            full_audio = np.concatenate(self.buffer)
                            
                            # 최소 길이 확인 (더 짧은 발화도 허용)
                            duration = len(full_audio) / self.sample_rate
                            if duration >= self.min_speech_duration:
                                print(f"음성 감지 종료 (길이: {duration:.2f}초) - 처리 중...")
                                # 별도 스레드에서 처리하여 대기 시간 감소
                                threading.Thread(
                                    target=self._transcribe, 
                                    args=(full_audio,),
                                    daemon=True
                                ).start()
                            else:
                                print(f"너무 짧은 음성 무시 ({duration:.2f}초)")
                            
                            # 버퍼 초기화
                            self.buffer = []
            else:
                time.sleep(0.01)
    
    def _transcribe(self, audio_data):
        """Whisper를 사용하여 오디오 인식 (최적화 버전)"""
        try:
            # 오디오 데이터를 float32로 변환
            audio_data = audio_data.astype(np.float32)
            
            # 음량 정규화
            if np.abs(audio_data).max() > 0:
                audio_data = audio_data / np.abs(audio_data).max()
            
            # Whisper 모델로 인식 (최적화된 설정)
            result = self.model.transcribe(
                audio_data, 
                language=self.language,
                fp16=torch.cuda.is_available(),
                initial_prompt="안녕하세요",  # 한국어 인식 개선
                beam_size=1,  # 속도 최적화
                best_of=1,    # 속도 최적화
            )
            
            # 결과 추출
            text = result["text"].strip()
            
            # 중복 입력 방지
            if hasattr(self, 'last_text') and self.last_text == text:
                print(f"중복 텍스트 무시: {text}")
                return
            
            if text:  # 빈 텍스트가 아닌 경우에만
                print(f"인식된 텍스트: {text}")
                self.result_queue.put(text)
                self.last_text = text  # 마지막 텍스트 저장
            else:
                print("인식된 텍스트 없음")
        except Exception as e:
            print(f"음성 인식 오류: {e}")