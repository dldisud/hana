from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.spinner import Spinner
from PyInquirer import prompt

console = Console()

def display_welcome():
    """시작 화면을 표시합니다."""
    console.print(Panel.fit(
        "[bold magenta]Hana AI Streamer[/bold magenta]\n\n[green]AI와 함께하는 새로운 스트리밍 경험[/green]",
        title="Welcome",
        border_style="cyan"
    ))

def select_mode():
    """사용자가 실행 모드를 선택하도록 합니다."""
    questions = [
        {
            'type': 'list',
            'name': 'mode',
            'message': '실행할 모드를 선택하세요:',
            'choices': [
                {'name': '1. 텍스트 입력 모드', 'value': '1'},
                {'name': '2. 음성 인식 모드', 'value': '2'},
                {'name': '3. 채팅 스트리밍 모드', 'value': '3'},
            ],
        }
    ]
    answers = prompt(questions)
    return answers.get('mode')

def display_chat(username, text, color="white"):
    """대화 내용을 패널에 표시합니다."""
    panel = Panel(
        Syntax(text, "python", theme="monokai", line_numbers=False),
        title=f"[bold {color}]{username}[/bold {color}]",
        border_style=color,
        expand=False
    )
    console.print(panel)

def display_status(message, spinner_style="dots"):
    """상태 메시지를 스피너와 함께 표시합니다."""
    with Spinner(spinner_style, text=message) as spinner:
        # 이 부분은 실제 작업이 수행되는 동안 스피너를 표시하기 위한 것입니다.
        # 실제 작업은 이 함수를 호출한 곳에서 이루어져야 합니다.
        pass

def get_api_keys():
    """사용자로부터 API 키를 안전하게 입력받습니다."""
    questions = [
        {
            'type': 'password',
            'name': 'gemini_api_key',
            'message': 'Gemini API 키를 입력하세요:',
        },
        {
            'type': 'password',
            'name': 'google_tts_api_key',
            'message': 'Google TTS API 키를 입력하세요:',
        },
        {
            'type': 'password',
            'name': 'youtube_api_key',
            'message': 'YouTube API 키 (선택 사항):',
        }
    ]
    console.print(Panel.fit("[bold yellow]API 키를 입력해주세요.[/bold yellow]\n키는 입력 시 화면에 표시되지 않습니다."))
    answers = prompt(questions)
    return answers

def get_user_input(prompt_message="나: "):
    """사용자 입력을 받습니다."""
    return console.input(f"[bold green]{prompt_message}[/bold green]")
