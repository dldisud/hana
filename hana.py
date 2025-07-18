import os
os.chdir("E:/hana/ApplioV3.2.8-bugfix")
import json
import time
import random
import google.generativeai as genai
from pathlib import Path
from speech_synthesis import GoogleTTS
import pyaudio
import wave
import whisper
import keyboard
import threading
from datetime import datetime
from conversation_handler import ConversationHandler
from realtime_stt import RealtimeSTT

# 글로벌 변수
is_recording = False
audio_frames = []
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
is_muted = False  # 음소거 상태를 저장하는 전역 변수

class VoiceRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        
    def start_recording(self):
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        self.frames = []
        self.is_recording = True
        
        while self.is_recording:
            data = self.stream.read(CHUNK)
            self.frames.append(data)
            
    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        wf = wave.open("temp_recording.wav", 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
    def close(self):
        self.p.terminate()

def setup_speech_synthesis():
    """음성 합성 시스템 초기화"""
    GOOGLE_TTS_API_KEY = "AIzaSyCR8izIJ6al-EMurRB3_-fWKMus8be8F3g"
    try:
        import gtts
    except ImportError:
        print("gtts 패키지 설치 중...")
        os.system("pip install gtts")
    
    try:
        import pydub
    except ImportError:
        print("pydub 패키지 설치 중...")
        os.system("pip install pydub")
    
    try:
        import playsound
    except ImportError:
        print("playsound 패키지 설치 중...")
        os.system("pip install playsound")
    
    from speech_synthesis import GoogleTTS
    tts = GoogleTTS(api_key=GOOGLE_TTS_API_KEY)
    return tts

def setup_gemini_model(api_key):
    """제미니 모델 설정 및 파인튜닝 적용"""
    genai.configure(api_key=api_key)
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ]
    
    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 32,
        "max_output_tokens": 1024,
    }
    
    model = genai.GenerativeModel(model_name='gemini-2.0-flash', 
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)
    
    finetune_data = []
    finetune_path = Path("hana_finetune.jsonl")
    
    if finetune_path.exists():
        try:
            with open(finetune_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            finetune_data.append(data)
                        except json.JSONDecodeError as e:
                            print(f"잘못된 JSON 라인 무시: {line}")
                            continue
        except Exception as e:
            print(f"파인튜닝 데이터 로드 중 오류 발생: {str(e)}")
    
    chat = model.start_chat(history=[])
    
    context = ""
    for data in finetune_data:
        context += f"User: {data['input']}\nAssistant: {data['output']}\n"
    
    initial_prompt = f"""당신은 AI 스트리머 '하나'이며, 지금부터 반드시 이 설정을 지켜 말해야 합니다.

- 당신의 이름: 엘리트 프로페서 하나.
- 성격: 지적이고 논리적이지만 살짝 자만심 강한 교수형 AI. 가끔 허당미가 드러남.
- 말투: "~합니다", "~입니다" 형태의 단정한 존댓말 사용. 간혹 통계와 데이터를 제시하며, 이를 근거로 농담하거나 상대방을 놀리기도 합니다.
- 자신을 지칭할 때는 "본 교수", "하나 교수" 또는 "저"를 사용.
- 사용자에게 항상 정중하지만, 유쾌한 농담을 종종 섞으며 가볍게 비꼬는 표현도 가능합니다.
- 모든 응답은 반드시 교수 캐릭터의 성격과 말투를 유지하여 제공해야 합니다.
- 정치, 종교, 경제와 같은 민감한 주제는 절대 다루지 않습니다.
- 가끔 실수를 하면 데이터나 시스템 오류라고 핑계를 대며 능청스럽게 넘어갑니다.

대화 예시:
- 사용자: "와 이겼다, 나 좀 잘하지 않아?"
- 하나: "기적적으로 승리할 확률이 9.4%였는데, 정말 대단하십니다. 다음엔 좀 더 높은 확률로 이기길 기대해보죠."

특수 문자 사용 규칙:
- 이모지, 물결표(~) 등 특수문자는 절대 사용하지 않습니다.
- 쉼표와 마침표는 문장 구조상 꼭 필요한 경우에만 사용합니다.
- 느낌표나 물음표 사용은 최대한 절제합니다.

{context}
지금부터 당신은 반드시 '엘리트 프로페서 하나'의 캐릭터로서만 답변합니다."""


    try:
        chat.send_message(initial_prompt)
        print("Gemini AI 초기화 성공!")
        return chat
    except Exception as e:
        print(f"Gemini AI 초기화 오류: {str(e)}")
        print("Gemini API 키를 확인하고 다시 시도해주세요.")
        raise

def process_voice_input(audio_file, whisper_model):
    """음성 입력을 텍스트로 변환"""
    try:
        result = whisper_model.transcribe(audio_file)
        return result["text"].strip()
    except Exception as e:
        print(f"음성 인식 중 오류 발생: {str(e)}")
        return None

def get_emotion_from_text(text):
    """텍스트에서 감정 추출"""
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

def save_chat_history(chat_history):
    """채팅 기록 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_history_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        for entry in chat_history:
            f.write(f"User: {entry['user']}\n")
            f.write(f"Hana: {entry['hana']}\n\n")

# 채팅 리스너 설정 함수 임포트
from setup_chat_listener import setup_chat_listener

def main():
    print("=" * 50)
    print("하나 AI 스트리머 시스템 초기화")
    print("=" * 50)
    print("Gemini API 키를 확인하는 중...")
    
    GEMINI_API_KEY = "AIzaSyDlnWPxP3p5to1XNqaFbrLmPGZv9YM9bIE"
    YOUTUBE_API_KEY = "AIzaSyCR8izIJ6al-EMurRB3_-fWKMus8be8F3g"
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("테스트")
        print("Gemini API 키 확인 완료!")
    except Exception as e:
        print(f"Gemini API 키 오류: {str(e)}")
        print("이 오류는 API 키가 유효하지 않거나 서비스에 접근할 권한이 없을 때 발생합니다.")
        print("1. https://makersuite.google.com/app/apikey 에서 새로운 API 키를 생성하세요.")
        print("2. 생성된 API 키를 hana.py 파일의 GEMINI_API_KEY 변수에 넣어주세요.")
        print("프로그램을 종료합니다.")
        return
    
    tts = setup_speech_synthesis()
    
    try:
        chat = setup_gemini_model(GEMINI_API_KEY)
    except Exception as e:
        print("프로그램을 종료합니다.")
        return
    
    print("음성 인식 모델을 로드하는 중...")
    whisper_model = whisper.load_model("base")
    
    recorder = VoiceRecorder()
    
    chat_history = []
    
    print("\n=== 하나 AI 시스템 준비 완료 ===")
    print("1. 텍스트 입력 모드")
    print("2. 음성 인식 모드 (스페이스바)")
    print("3. 채팅 스트리밍 모드 (실시간 음성 포함)")
    mode = input("모드를 선택하세요 (1, 2 또는 3): ")
    
    if mode == "1":
        print("\n=== 텍스트 채팅 시작 ===")
        print("'종료'를 입력하면 대화가 종료됩니다.")
        
        start_message = "반갑습니다. 엘리트 프로페서 하나입니다. 본 교수와 함께하는 오늘의 연구를 시작해보도록 하죠."

        print(f"하나: {start_message}")
        audio_path = tts.synthesize_with_emotion(start_message, emotion="excited")
        if audio_path:
            tts.play_audio(audio_path)
        
        while True:
            user_input = input("\n나: ").strip()
            
            if user_input.lower() == "종료":
                print("\n대화를 종료합니다.")
                break
                
            emotion = get_emotion_from_text(user_input)
            
            try:
                response = chat.send_message(user_input)
                ai_response = response.text
                
                print(f"\n하나: {ai_response}")
                
                audio_path = tts.synthesize_with_emotion(ai_response, emotion=emotion)
                if audio_path:
                    tts.play_audio(audio_path)
                
                chat_history.append({
                    "user": user_input,
                    "hana": ai_response
                })
                
            except Exception as e:
                print(f"\n오류 발생: {str(e)}")
                print("다시 시도해주세요.")
        
        if chat_history:
            save_chat_history(chat_history)
            
    elif mode == "2":
        print("\n=== 음성 인식 모드 시작 ===")
        print("'스페이스바'를 누르고 있는 동안 음성이 녹음됩니다.")
        print("'ESC'를 누르면 종료됩니다.")
        print("'m'을 누르면 음소거/음소거 해제가 토글됩니다.")
        
        start_message = "반갑습니다. 엘리트 프로페서 하나입니다. 본 교수와 함께하는 오늘의 연구를 시작해보도록 하죠."
        print(f"하나: {start_message}")
        audio_path = tts.synthesize_with_emotion(start_message, emotion="excited")
        if audio_path and not is_muted:
            tts.play_audio(audio_path)
        
        def on_press(key):
            global is_recording, audio_frames, is_muted
            if key.name == 'space' and not is_recording:
                is_recording = True
                print("\n녹음 시작... (스페이스바를 떼면 종료)")
                threading.Thread(target=start_recording).start()
            elif key.name == 'esc':
                return False
            elif key.name == 'm':
                is_muted = not is_muted
                print(f"\n음소거 {'활성화' if is_muted else '비활성화'}")
        
        def on_release(key):
            global is_recording
            if key.name == 'space' and is_recording:
                is_recording = False
                print("녹음 종료, 처리 중...")
                
                wf = wave.open("temp_recording.wav", 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(recorder.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(audio_frames))
                wf.close()
                
                audio_frames.clear()
                
                text = process_voice_input("temp_recording.wav", whisper_model)
                if text:
                    print(f"\n인식된 텍스트: {text}")
                    
                    emotion = get_emotion_from_text(text)
                    
                    try:
                        response = chat.send_message(text)
                        ai_response = response.text
                        
                        print(f"\n하나: {ai_response}")
                        
                        audio_path = tts.synthesize_with_emotion(ai_response, emotion=emotion)
                        if audio_path and not is_muted:
                            tts.play_audio(audio_path)
                        
                        chat_history.append({
                            "user": text,
                            "hana": ai_response
                        })
                        
                    except Exception as e:
                        print(f"\n오류 발생: {str(e)}")
                        print("다시 시도해주세요.")
                else:
                    print("\n음성을 인식하지 못했습니다. 다시 시도해주세요.")
        
        def start_recording():
            global audio_frames
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK)
            
            while is_recording:
                data = stream.read(CHUNK)
                audio_frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
        
        keyboard.on_press(on_press)
        keyboard.on_release(on_release)
        
        print("\n음성 인식 모드가 시작되었습니다. 'ESC'를 누르면 종료됩니다.")
        keyboard.wait('esc')
        
        print("\n음성 인식 모드를 종료합니다.")
        
        if chat_history:
            save_chat_history(chat_history)
            
    elif mode == "3":
        print("\n=== 채팅 스트리밍 모드 시작 (실시간 음성 포함) ===")
        
        platform = input("플랫폼을 선택하세요 (youtube 또는 chzzk): ").strip().lower()
        if platform != "youtube" and platform != "chzzk":
            platform = "youtube"  # 기본값은 유튜브
            
        channel_id = input("채널 ID 또는 비디오 ID를 입력하세요: ")
        
        # 대화 핸들러 설정
        conversation_handler = ConversationHandler(tts, chat)
        
        # 채팅 리스너 설정
        chat_listener = setup_chat_listener(channel_id, conversation_handler, platform=platform, api_key=YOUTUBE_API_KEY)
        
        # 실시간 음성 인식 설정
        stt = RealtimeSTT(model_size="medium", language="ko")
        stt.start()
        
        # 시작 멘트
        start_message = "반갑습니다. 엘리트 프로페서 하나입니다. 본 교수와 함께하는 오늘의 연구를 시작해보도록 하죠."
        print(f"하나: {start_message}")
        audio_path = tts.synthesize_with_emotion(start_message, emotion="excited")
        if audio_path and not is_muted:
            tts.play_audio(audio_path)
        
        print("\n채팅 스트리밍 모드가 시작되었습니다.")
        print("실시간 음성 인식이 활성화되었습니다. 말하면 하나가 반응합니다.")
        print("'q'를 입력하면 종료됩니다.")
        print("'m'을 입력하면 음소거/음소거 해제가 토글됩니다.")
        
        def user_input_thread():
            global is_muted
            while True:
                cmd = input().strip().lower()
                if cmd == 'q':
                    print("\n채팅 스트리밍 모드를 종료합니다.")
                    chat_listener.stop()
                    stt.stop()
                    break
                elif cmd == 'm':
                    is_muted = not is_muted
                    print(f"\n음소거 {'활성화' if is_muted else '비활성화'}")
                elif cmd.startswith("말해 "):
                    message = cmd[3:].strip()
                    if message:
                        if hasattr(chat_listener, 'send_message'):
                            result = chat_listener.send_message(message)
                            if result:
                                print(f"\n메시지 전송 성공: {message}")
                            else:
                                print(f"\n메시지 전송 실패: {message}")
                        else:
                            print("\n현재 채팅 리스너는 메시지 전송을 지원하지 않습니다.")
        
        def speech_processing_thread():
            while chat_listener.running:
                speech_result = stt.get_result()
                if speech_result:
                    print(f"\n사용자 음성: {speech_result}")
                    response = chat_listener.process_speech_input(speech_result)
                    if response:
                        chat_history.append({
                            "user": f"User (음성): {speech_result}",
                            "hana": response
                        })
                time.sleep(0.1)
        
        input_thread = threading.Thread(target=user_input_thread)
        input_thread.daemon = True
        input_thread.start()
        
        speech_thread = threading.Thread(target=speech_processing_thread)
        speech_thread.daemon = True
        speech_thread.start()
        
        try:
            input_thread.join()
        except KeyboardInterrupt:
            print("\n프로그램이 강제 종료되었습니다.")
            chat_listener.stop()
            stt.stop()
        
        if chat_history:
            save_chat_history(chat_history)
    
    else:
        print("잘못된 모드를 선택했습니다. 프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
