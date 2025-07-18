import os
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
import ui_handler
from PyInquirer import prompt

# 글로벌 변수
is_muted = False

class VoiceRecorder:
    def __init__(self, output_filename="temp_recording.wav"):
        self.output_filename = output_filename
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        self._thread = None
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

    def start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.frames = []
        self._thread = threading.Thread(target=self._record)
        self._thread.start()

    def _record(self):
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        while self.is_recording:
            data = self.stream.read(self.CHUNK)
            self.frames.append(data)

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def stop_recording_and_save(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self._thread:
            self._thread.join()

        wf = wave.open(self.output_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()

    def close(self):
        self.p.terminate()

def setup_speech_synthesis(google_tts_api_key):
    """음성 합성 시스템 초기화"""
    try:
        import gtts
    except ImportError:
        ui_handler.console.print("[bold yellow]gtts 패키지 설치 중...[/bold yellow]")
        os.system("pip install gtts")
    
    try:
        import pydub
    except ImportError:
        ui_handler.console.print("[bold yellow]pydub 패키지 설치 중...[/bold yellow]")
        os.system("pip install pydub")
    
    try:
        import playsound
    except ImportError:
        ui_handler.console.print("[bold yellow]playsound 패키지 설치 중...[/bold yellow]")
        os.system("pip install playsound")
    
    from speech_synthesis import GoogleTTS
    # rvc_lib_path는 사용자가 speech_synthesis.py에서 직접 수정해야 함
    tts = GoogleTTS(api_key=google_tts_api_key)
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
        "temperature": 0.2,
        "top_p": 1,
        "top_k": 32,
        "max_output_tokens": 1024,
    }
    
    model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest',
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
                            ui_handler.console.print(f"[bold red]잘못된 JSON 라인 무시: {line}[/bold red]")
                            continue
        except Exception as e:
            ui_handler.console.print(f"[bold red]파인튜닝 데이터 로드 중 오류 발생: {str(e)}[/bold red]")
    
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
        ui_handler.console.print("[green]Gemini AI 초기화 성공![/green]")
        return chat
    except Exception as e:
        ui_handler.console.print(f"[bold red]Gemini AI 초기화 오류: {str(e)}[/bold red]")
        raise

def process_voice_input(audio_file, whisper_model):
    """음성 입력을 텍스트로 변환"""
    try:
        result = whisper_model.transcribe(audio_file)
        return result["text"].strip()
    except Exception as e:
        ui_handler.console.print(f"[bold red]음성 인식 중 오류 발생: {str(e)}[/bold red]")
        return None

def get_emotion_from_text(text):
    """텍스트에서 감정 추출"""
    happy_keywords = ["좋아", "행복", "신나", "재미", "웃"]
    sad_keywords = ["슬퍼", "우울", "힘들", "아파", "싫어"]
    angry_keywords = ["화나", "짜증", "열받", "미쳐", "죽"]
    excited_keywords = ["대박", "와우", "멋져", "최고", "사랑"]
    
    text = text.lower()
    
    for word in happy_keywords:
        if word in text: return "happy"
    for word in sad_keywords:
        if word in text: return "sad"
    for word in angry_keywords:
        if word in text: return "angry"
    for word in excited_keywords:
        if word in text: return "excited"
            
    return "neutral"

def save_chat_history(chat_history):
    """채팅 기록 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_history_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        for entry in chat_history:
            f.write(f"User: {entry['user']}\n")
            f.write(f"Hana: {entry['hana']}\n\n")
    ui_handler.console.print(f"[green]채팅 기록이 {filename}에 저장되었습니다.[/green]")

# 채팅 리스너 설정 함수 임포트
from setup_chat_listener import setup_chat_listener

def main():
    ui_handler.display_welcome()

    api_keys = ui_handler.get_api_keys()
    gemini_api_key = api_keys.get('gemini_api_key')
    google_tts_api_key = api_keys.get('google_tts_api_key')
    youtube_api_key = api_keys.get('youtube_api_key')

    if not gemini_api_key or not google_tts_api_key:
        ui_handler.console.print("[bold red]필수 API 키가 입력되지 않았습니다. 프로그램을 종료합니다.[/bold red]")
        return

    try:
        with ui_handler.console.status("[bold yellow]Gemini API 키 확인 중...[/bold yellow]"):
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            model.generate_content("테스트")
        ui_handler.console.print("[green]Gemini API 키 확인 완료![/green]")
    except Exception as e:
        ui_handler.console.print(f"[bold red]Gemini API 키 오류:[/bold red] {e}")
        return

    with ui_handler.console.status("[bold yellow]음성 합성 시스템 초기화 중...[/bold yellow]"):
        tts = setup_speech_synthesis(google_tts_api_key)
    
    try:
        with ui_handler.console.status("[bold yellow]Gemini 모델 설정 중...[/bold yellow]"):
            chat = setup_gemini_model(gemini_api_key)
    except Exception as e:
        ui_handler.console.print(f"[bold red]Gemini 모델 설정 오류:[/bold red] {e}")
        return
    
    with ui_handler.console.status("[bold yellow]음성 인식 모델 로드 중...[/bold yellow]"):
        whisper_model = whisper.load_model("base")
    
    recorder = VoiceRecorder()
    chat_history = []
    
    mode = ui_handler.select_mode()

    if mode == "1":
        run_text_mode(tts, chat, chat_history)
    elif mode == "2":
        run_voice_mode(tts, chat, whisper_model, recorder, chat_history)
    elif mode == "3":
        run_streaming_mode(tts, chat, youtube_api_key, chat_history)
    else:
        ui_handler.console.print("[bold red]잘못된 모드를 선택했습니다. 프로그램을 종료합니다.[/bold red]")

def run_text_mode(tts, chat, chat_history):
    ui_handler.console.print(ui_handler.Panel.fit("[bold cyan]텍스트 채팅 시작[/bold cyan]\n'종료'를 입력하면 대화가 종료됩니다."))

    start_message = "반갑습니다. 엘리트 프로페서 하나입니다. 본 교수와 함께하는 오늘의 연구를 시작해보도록 하죠."
    ui_handler.display_chat("하나", start_message, color="magenta")

    with ui_handler.console.status("[bold yellow]음성 합성 중...[/bold yellow]"):
        audio_path = tts.synthesize_with_emotion(start_message, emotion="excited")
    if audio_path:
        tts.play_audio(audio_path)

    while True:
        user_input = ui_handler.get_user_input()
        
        if user_input.lower() == "종료":
            ui_handler.console.print("[bold yellow]대화를 종료합니다.[/bold yellow]")
            break
            
        emotion = get_emotion_from_text(user_input)

        try:
            with ui_handler.console.status("[bold yellow]하나가 답변을 생성 중입니다...[/bold yellow]"):
                response = chat.send_message(user_input)
                ai_response = response.text

            ui_handler.display_chat("하나", ai_response, color="magenta")

            with ui_handler.console.status("[bold yellow]음성 합성 중...[/bold yellow]"):
                audio_path = tts.synthesize_with_emotion(ai_response, emotion=emotion)
            if audio_path:
                tts.play_audio(audio_path)

            chat_history.append({"user": user_input, "hana": ai_response})
        except Exception as e:
            ui_handler.console.print(f"[bold red]오류 발생:[/bold red] {e}")

    if chat_history:
        save_chat_history(chat_history)

def run_voice_mode(tts, chat, whisper_model, recorder, chat_history):
    global is_muted
    ui_handler.console.print(ui_handler.Panel.fit("[bold cyan]음성 인식 모드 시작[/bold cyan]\n'스페이스바'를 누르고 있는 동안 음성이 녹음됩니다.\n'ESC'를 누르면 종료됩니다."))

    start_message = "반갑습니다. 엘리트 프로페서 하나입니다. 본 교수와 함께하는 오늘의 연구를 시작해보도록 하죠."
    ui_handler.display_chat("하나", start_message, color="magenta")

    with ui_handler.console.status("[bold yellow]음성 합성 중...[/bold yellow]"):
        audio_path = tts.synthesize_with_emotion(start_message, emotion="excited")
    if audio_path and not is_muted:
        tts.play_audio(audio_path)

    def handle_voice_input():
        recorder.start_recording()
        ui_handler.console.print("[bold yellow]녹음 시작... (스페이스바를 떼면 종료)[/bold yellow]")
        keyboard.wait('space', suppress=True)
        recorder.stop_recording_and_save()

        with ui_handler.console.status("[bold yellow]음성 처리 중...[/bold yellow]"):
            text = process_voice_input(recorder.output_filename, whisper_model)

        if text:
            ui_handler.display_chat("나 (음성)", text, color="green")
            emotion = get_emotion_from_text(text)
            try:
                with ui_handler.console.status("[bold yellow]하나가 답변을 생성 중입니다...[/bold yellow]"):
                    response = chat.send_message(text)
                    ai_response = response.text
                
                ui_handler.display_chat("하나", ai_response, color="magenta")

                with ui_handler.console.status("[bold yellow]음성 합성 중...[/bold yellow]"):
                    audio_path = tts.synthesize_with_emotion(ai_response, emotion=emotion)
                if audio_path and not is_muted:
                    tts.play_audio(audio_path)
                
                chat_history.append({"user": text, "hana": ai_response})
            except Exception as e:
                ui_handler.console.print(f"[bold red]오류 발생:[/bold red] {e}")
        else:
            ui_handler.console.print("[bold red]음성을 인식하지 못했습니다. 다시 시도해주세요.[/bold red]")

    while True:
        ui_handler.console.print("\n[bold]스페이스바를 눌러 녹음을 시작하세요.[/bold] (ESC: 종료, m: 음소거 토글)")
        key = keyboard.read_key()
        if key == 'space':
            handle_voice_input()
        elif key == 'm':
            is_muted = not is_muted
            ui_handler.console.print(f"[bold yellow]음소거 {'활성화' if is_muted else '비활성화'}[/bold yellow]")
        elif key == 'esc':
            break

    ui_handler.console.print("[bold yellow]음성 인식 모드를 종료합니다.[/bold yellow]")
    recorder.close()
    if chat_history:
        save_chat_history(chat_history)

def run_streaming_mode(tts, chat, youtube_api_key, chat_history):
    global is_muted
    ui_handler.console.print(ui_handler.Panel.fit("[bold cyan]채팅 스트리밍 모드 시작[/bold cyan]"))

    questions = [
        {'type': 'list', 'name': 'platform', 'message': '플랫폼을 선택하세요:', 'choices': ['youtube', 'chzzk']},
        {'type': 'input', 'name': 'channel_id', 'message': '채널 ID 또는 비디오 ID를 입력하세요:'}
    ]
    answers = prompt(questions)
    platform = answers.get('platform')
    channel_id = answers.get('channel_id')

    if not channel_id:
        ui_handler.console.print("[bold red]채널 ID가 입력되지 않았습니다. 스트리밍 모드를 종료합니다.[/bold red]")
        return

    conversation_handler = ConversationHandler(tts, chat)

    with ui_handler.console.status("[bold yellow]채팅 리스너 설정 중...[/bold yellow]"):
        chat_listener = setup_chat_listener(channel_id, conversation_handler, platform=platform, api_key=youtube_api_key)

    stt = RealtimeSTT(model_size="medium", language="ko")
    stt.start()

    start_message = "반갑습니다. 엘리트 프로페서 하나입니다. 본 교수와 함께하는 오늘의 연구를 시작해보도록 하죠."
    ui_handler.display_chat("하나", start_message, color="magenta")

    with ui_handler.console.status("[bold yellow]음성 합성 중...[/bold yellow]"):
        audio_path = tts.synthesize_with_emotion(start_message, emotion="excited")
    if audio_path and not is_muted:
        tts.play_audio(audio_path)

    ui_handler.console.print(ui_handler.Panel.fit("[bold green]채팅 스트리밍 모드가 시작되었습니다.[/bold green]\n실시간 음성 인식이 활성화되었습니다. 말하면 하나가 반응합니다.\n'q'를 입력하면 종료됩니다."))

    def user_input_thread():
        global is_muted
        while True:
            cmd = input().strip().lower()
            if cmd == 'q':
                ui_handler.console.print("[bold yellow]채팅 스트리밍 모드를 종료합니다.[/bold yellow]")
                chat_listener.stop()
                stt.stop()
                break
            elif cmd == 'm':
                is_muted = not is_muted
                ui_handler.console.print(f"[bold yellow]음소거 {'활성화' if is_muted else '비활성화'}[/bold yellow]")
            elif cmd.startswith("말해 "):
                message = cmd[3:].strip()
                if message:
                    if hasattr(chat_listener, 'send_message'):
                        result = chat_listener.send_message(message)
                        if result:
                            ui_handler.console.print(f"\n[green]메시지 전송 성공: {message}[/green]")
                        else:
                            ui_handler.console.print(f"\n[red]메시지 전송 실패: {message}[/red]")
                    else:
                        ui_handler.console.print("\n[red]현재 채팅 리스너는 메시지 전송을 지원하지 않습니다.[/red]")

    def speech_processing_thread():
        while chat_listener.running:
            speech_result = stt.get_result()
            if speech_result:
                ui_handler.display_chat("나 (음성)", speech_result, color="green")
                response = chat_listener.process_speech_input(speech_result)
                if response:
                    chat_history.append({"user": f"User (음성): {speech_result}", "hana": response})
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
        ui_handler.console.print("\n[bold red]프로그램이 강제 종료되었습니다.[/bold red]")
        chat_listener.stop()
        stt.stop()

    if chat_history:
        save_chat_history(chat_history)

if __name__ == "__main__":
    main()
