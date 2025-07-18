import os
import requests
import json
import wave
import pyaudio
import base64
from pathlib import Path
import sys
import torch  # torch 임포트 추가
from fairseq.checkpoint_utils import load_model_ensemble_and_task_from_hf_hub

sys.path.append("E:/hana/ApplioV3.2.8-bugfix")
from rvc.infer.infer import VoiceConverter
from rvc.configs.config import Config

class GoogleTTS:
    def __init__(self, api_key, temp_dir="E:/hana/temp", rvc_model_path="E:/hana/ApplioV3.2.8-bugfix/logs/Arcueid Brunestud/model.pth", rvc_index_path="E:/hana/ApplioV3.2.8-bugfix/logs/Arcueid Brunestud/model.index"):
        self.api_key = api_key
        self.temp_dir = temp_dir
        self.default_language = "ko-KR"
        self.default_voice = "ko-KR-Chirp3-HD-Leda"
        
        os.makedirs(temp_dir, exist_ok=True)
        
        self.emotion_params = {
            "happy": {"rate": 1.0, "volume": 0},
            "sad": {"rate": 1.0, "volume": 0},
            "angry": {"rate": 1.0, "volume": 0},
            "neutral": {"rate": 1.0, "volume": 0},
            "excited": {"rate": 1.0, "volume": 0},
            "calm": {"rate": 1.0, "volume": 0}
        }

        self.rvc_model_path = rvc_model_path
        self.rvc_index_path = rvc_index_path
        self.vc = VoiceConverter()
        self.config = Config()
        if torch.cuda.is_available():
            self.config.device = "cuda:0"
            self.config.is_half = True
        else:
            self.config.device = "cpu"
            self.config.is_half = False

    def _get_speaking_rate(self, emotion):
        if emotion in self.emotion_params:
            return self.emotion_params[emotion]["rate"]
        return 1.0

    def _get_volume(self, emotion):
        if emotion in self.emotion_params:
            return self.emotion_params[emotion]["volume"]
        return 0

    def synthesize_with_emotion(self, text, emotion="neutral", speed=1.0, temperature=None):
        try:
            print(f"감정({emotion})을 담아 음성 생성 중...")
            speaking_rate = self._get_speaking_rate(emotion) if speed == 1.0 else speed
            volume = self._get_volume(emotion)
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
            request_data = {
                "input": {"text": text},
                "voice": {"languageCode": self.default_language, "name": self.default_voice},
                "audioConfig": {"audioEncoding": "LINEAR16", "speakingRate": speaking_rate, "volumeGainDb": volume}
            }
            response = requests.post(url, json=request_data)
            if response.status_code != 200:
                print(f"TTS API 오류: {response.status_code}, {response.text}")
                return self._use_fallback_tts(text)
            
            audio_content = response.json().get("audioContent")
            if not audio_content:
                print("오디오 콘텐츠를 받지 못했습니다.")
                return self._use_fallback_tts(text)

            base_output_path = os.path.join(self.temp_dir, "base_output.wav")
            with open(base_output_path, "wb") as f:
                f.write(base64.b64decode(audio_content))

            # 샘플레이트 확인
            with wave.open(base_output_path, 'rb') as wf:
                base_sample_rate = wf.getframerate()
                print(f"base_output.wav 샘플레이트: {base_sample_rate} Hz")

            final_output_path = os.path.join(self.temp_dir, "output.wav")
            print(f"{emotion} 감정으로 RVC 변환 중...")
            self._apply_rvc(base_output_path, final_output_path, emotion)

            if not os.path.exists(final_output_path) or os.path.getsize(final_output_path) < 100:
                print("RVC 변환 후 파일 문제 발생.")
                return base_output_path

            try:
                with wave.open(final_output_path, 'rb') as wave_file:
                    _ = wave_file.getframerate()
                print("WAV 파일 검증 완료")
            except Exception as e:
                print(f"WAV 파일 검증 실패: {str(e)}")
                return base_output_path

            return final_output_path

        except Exception as e:
            print(f"감정 음성 합성 중 오류 발생: {str(e)}")
            return self._use_fallback_tts(text)

    def _apply_rvc(self, input_path, output_path, emotion):
        f0_up_key = 0
        if emotion == "happy" or emotion == "excited":
            f0_up_key = 2
        elif emotion == "sad" or emotion == "calm":
            f0_up_key = -2
        elif emotion == "angry":
            f0_up_key = 1

        self.vc.convert_audio(
            audio_input_path=input_path,
            audio_output_path=output_path,
            model_path=self.rvc_model_path,
            index_path=self.rvc_index_path,
            pitch=f0_up_key,
            f0_method="rmvpe",
            index_rate=0.75,
            volume_envelope=1.0,
            protect=0.5,
            hop_length=128,
            split_audio=False,
            f0_autotune=False,
            filter_radius=3,
            embedder_model="contentvec",
            embedder_model_custom=None,
            clean_audio=False,
            export_format="WAV",
            post_process=False,
            resample_sr=0,
            sid=0
        )

    def _use_fallback_tts(self, text):
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            print("대체 TTS 엔진(gTTS) 사용 중...")
            output_path = os.path.join(self.temp_dir, "output.wav")
            temp_mp3 = os.path.join(self.temp_dir, "temp.mp3")
            tts = gTTS(text=text, lang='ko')
            tts.save(temp_mp3)
            sound = AudioSegment.from_mp3(temp_mp3)
            sound.export(output_path, format="wav")
            return output_path
        except Exception as e:
            print(f"대체 TTS 사용 중 오류 발생: {str(e)}")
            return None

    def play_audio(self, file_path):
        try:
            if not os.path.exists(file_path):
                print(f"파일을 찾을 수 없습니다: {file_path}")
                return
            wf = wave.open(file_path, 'rb')
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                          channels=wf.getnchannels(),
                          rate=wf.getframerate(),
                          output=True)
            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            print(f"오디오 재생 중 오류 발생: {str(e)}")