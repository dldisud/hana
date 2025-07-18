import os
import requests
import json
import re
import wave
import pyaudio
import base64
from pathlib import Path

class GoogleTTS:
    def __init__(self, api_key, temp_dir="E:/hana/temp"):
        self.api_key = api_key
        self.temp_dir = temp_dir
        self.default_language = "ko-KR"
        self.default_voice = "ko-KR-Chirp3-HD-Leda"  # HD 음성으로 설정
        
        # 임시 디렉토리 생성
        os.makedirs(temp_dir, exist_ok=True)
        
        # 감정별 음성 매개변수
        self.emotion_params = {
            "happy": {"rate": 1.2, "volume": 2},
            "sad": {"rate": 0.8, "volume": -2},
            "angry": {"rate": 1.3, "volume": 4},
            "neutral": {"rate": 1.0, "volume": 0},
            "excited": {"rate": 1.4, "volume": 3},
            "calm": {"rate": 0.9, "volume": -1}
        }

    def _get_speaking_rate(self, emotion):
        """감정에 따른 말하기 속도 반환"""
        if emotion and emotion in self.emotion_params:
            return self.emotion_params[emotion]["rate"]
        return 1.0

    def _get_volume(self, emotion):
        """감정에 따른 볼륨 반환"""
        if emotion and emotion in self.emotion_params:
            return self.emotion_params[emotion]["volume"]
        return 0

    def synthesize(self, text, voice_name=None, language_code=None, emotion=None):
        """텍스트를 음성으로 합성"""
        try:
            voice_name = voice_name or self.default_voice
            language_code = language_code or self.default_language
            
            # 전처리 없이 원본 텍스트 사용
            print(f"Google Cloud TTS로 음성 생성 중: {text[:50]}...")
            
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
            
            # HD 음성에 맞게 구성 (pitch 제외)
            request_data = {
                "input": {"text": text},  # 원본 텍스트 그대로 사용
                "voice": {
                    "languageCode": language_code,
                    "name": voice_name
                },
                "audioConfig": {
                    "audioEncoding": "LINEAR16",
                    "speakingRate": self._get_speaking_rate(emotion),
                    "volumeGainDb": self._get_volume(emotion)
                }
            }
            
            response = requests.post(url, json=request_data)
            
            if response.status_code != 200:
                print(f"TTS API 오류: {response.status_code}")
                print(f"오류 내용: {response.text}")
                return self._use_fallback_tts(text)
                
            response_json = response.json()
            audio_content = response_json.get("audioContent")
            
            if not audio_content:
                print("오디오 콘텐츠를 받지 못했습니다.")
                return self._use_fallback_tts(text)
                
            output_path = os.path.join(self.temp_dir, "output.wav")
            
            # Base64 디코딩 및 파일 저장
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(audio_content))
                
            # 파일 검증
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                print("생성된 오디오 파일이 너무 작거나 존재하지 않습니다.")
                return self._use_fallback_tts(text)
                
            try:
                # WAV 파일 유효성 검사
                with wave.open(output_path, 'rb') as wave_file:
                    _ = wave_file.getframerate()
                print("WAV 파일 검증 완료")
            except Exception as e:
                print(f"WAV 파일 검증 실패: {str(e)}")
                return self._use_fallback_tts(text)
                
            return output_path
            
        except Exception as e:
            print(f"음성 합성 중 오류 발생: {str(e)}")
            return self._use_fallback_tts(text)

    def synthesize_with_emotion(self, text, emotion="neutral", speed=1.0, temperature=None):
        """감정을 담아 텍스트를 음성으로 변환"""
        try:
            # 전처리 없이 원본 텍스트 사용
            print(f"감정({emotion})을 담아 음성 생성 중...")
            
            # 감정에 따른 속도 및 볼륨 조정
            speaking_rate = self._get_speaking_rate(emotion) if speed == 1.0 else speed
            volume = self._get_volume(emotion)
            
            # API URL 구성
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
            
            # 요청 데이터 구성 (HD 음성은 pitch 제외)
            request_data = {
                "input": {"text": text},  # 원본 텍스트 그대로 사용
                "voice": {
                    "languageCode": self.default_language,
                    "name": self.default_voice
                },
                "audioConfig": {
                    "audioEncoding": "LINEAR16",
                    "speakingRate": speaking_rate,
                    "volumeGainDb": volume
                }
            }
            
            response = requests.post(url, json=request_data)
            
            if response.status_code != 200:
                print(f"TTS API 오류: {response.status_code}")
                print(f"오류 내용: {response.text}")
                return self._use_fallback_tts(text)
            
            response_json = response.json()
            audio_content = response_json.get("audioContent")
            
            if not audio_content:
                print("오디오 콘텐츠를 받지 못했습니다.")
                return self._use_fallback_tts(text)
            
            output_path = os.path.join(self.temp_dir, "output.wav")
            
            # Base64 디코딩 및 파일 저장
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(audio_content))
            
            # 파일 검증
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                print("생성된 오디오 파일이 너무 작거나 존재하지 않습니다.")
                return self._use_fallback_tts(text)
            
            try:
                # WAV 파일 유효성 검사
                with wave.open(output_path, 'rb') as wave_file:
                    _ = wave_file.getframerate()
                print("WAV 파일 검증 완료")
            except Exception as e:
                print(f"WAV 파일 검증 실패: {str(e)}")
                return self._use_fallback_tts(text)
            
            return output_path
            
        except Exception as e:
            print(f"감정 음성 합성 중 오류 발생: {str(e)}")
            return self._use_fallback_tts(text)

    def _use_fallback_tts(self, text):
        """Google TTS 실패 시 gTTS 사용"""
        try:
            # gTTS 사용을 위한 임포트
            from gtts import gTTS
            import tempfile
            
            print("대체 TTS 엔진(gTTS) 사용 중...")
            
            output_path = os.path.join(self.temp_dir, "output.wav")
            temp_mp3 = os.path.join(self.temp_dir, "temp.mp3")
            
            # gTTS로 MP3 생성
            tts = gTTS(text=text, lang='ko')
            tts.save(temp_mp3)
            
            # MP3를 WAV로 변환 (pydub 사용)
            try:
                from pydub import AudioSegment
                sound = AudioSegment.from_mp3(temp_mp3)
                sound.export(output_path, format="wav")
                return output_path
            except ImportError:
                print("pydub를 찾을 수 없어 MP3 형식 그대로 사용합니다.")
                return temp_mp3
                
        except Exception as e:
            print(f"대체 TTS 사용 중 오류 발생: {str(e)}")
            return None

    def play_audio(self, file_path):
        """WAV 파일 재생"""
        try:
            if not os.path.exists(file_path):
                print(f"파일을 찾을 수 없습니다: {file_path}")
                return
                
            # 파일 확장자 확인
            is_mp3 = file_path.lower().endswith('.mp3')
            
            if is_mp3:
                # MP3 재생 (playsound 사용)
                try:
                    from playsound import playsound
                    playsound(file_path)
                    return
                except ImportError:
                    print("playsound를 찾을 수 없습니다. pyaudio로 시도합니다.")
                    # MP3를 지원하지 않으므로 여기서 재생 실패
                    return
            
            # WAV 파일 유효성 검사
            try:
                wf = wave.open(file_path, 'rb')
            except Exception as e:
                print(f"WAV 파일 열기 실패: {str(e)}")
                return
            
            # PyAudio 객체 생성
            p = pyaudio.PyAudio()
            
            # 스트림 열기
            try:
                stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                              channels=wf.getnchannels(),
                              rate=wf.getframerate(),
                              output=True)
                
                # 청크 단위로 데이터 읽고 재생
                chunk = 1024
                data = wf.readframes(chunk)
                while data:
                    stream.write(data)
                    data = wf.readframes(chunk)
                
                # 스트림 정리
                stream.stop_stream()
                stream.close()
            except Exception as e:
                print(f"오디오 스트림 재생 중 오류: {str(e)}")
            finally:
                p.terminate()
            
        except Exception as e:
            print(f"오디오 재생 중 오류 발생: {str(e)}")