import flet as ft
import requests
import json
import threading
import time
import os
import asyncio

os.makedirs("assets", exist_ok=True)

API_URL = os.getenv("USTAAD_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 30
SSE_CONNECT_TIMEOUT_SECONDS = 10
SSE_READ_TIMEOUT_SECONDS = 65


# Module-level state management
class AppState:
    loading_bubble = None
    loading_emoji = None
    loading_text = None
    loading_active = threading.Event()


def ui_call(page, callback, *args, **kwargs):
    """Ensure UI updates run on the Flet UI thread."""
    try:
        page.call_from_thread(lambda: callback(*args, **kwargs))
    except Exception:
        pass


def add_message(page, chat_list, text, is_user=False, reasoning_text=None, action_button=None):
    """Adds a chat bubble to the UI."""
    msg_color = ft.Colors.BLUE_100 if is_user else ft.Colors.GREEN_100
    align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
    
    content_column = ft.Column([
        ft.Text(text, size=15, color=ft.Colors.BLACK87, selectable=True)
    ])
    
    if action_button:
        content_column.controls.append(action_button)
    
    if reasoning_text:
        reasoning_view = ft.Text(reasoning_text, size=13, color=ft.Colors.GREY_800, selectable=True, visible=False)
        
        def toggle_reasoning(e):
            reasoning_view.visible = not reasoning_view.visible
            page.update()
            
        toggle_btn = ft.TextButton("View Detailed Explanation & Calculations 📊", on_click=toggle_reasoning)
        content_column.controls.append(toggle_btn)
        content_column.controls.append(reasoning_view)

    chat_list.controls.append(
        ft.Row(
            [
                ft.Container(
                    content=content_column,
                    bgcolor=msg_color,
                    padding=15,
                    border_radius=12,
                    width=300,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.Colors.BLACK12, offset=ft.Offset(0, 2))
                )
            ],
            alignment=align
        )
    )
    page.update()


def remove_loading_bubble(chat_list):
    """Removes the loading bubble from chat."""
    if AppState.loading_bubble in chat_list.controls:
        chat_list.controls.remove(AppState.loading_bubble)
    AppState.loading_bubble = None


def finish_request_ui(page, chat_list, user_input, send_btn):
    """Finishes the request UI state."""
    AppState.loading_active.clear()
    remove_loading_bubble(chat_list)
    user_input.disabled = False
    send_btn.disabled = False
    page.update()


def append_log_entry(page, log_list, step: str, data_str: str):
    """Appends an entry to the debug logs."""
    log_list.controls.append(
        ft.Text(f"[{step}] {data_str}", size=11, color=ft.Colors.GREY_700, font_family="monospace")
    )
    if len(log_list.controls) > 30:
        log_list.controls.pop(0)
    page.update()


def update_loading_ui(emoji: str, text: str):
    """Updates the loading animation display."""
    if AppState.loading_emoji is None or AppState.loading_text is None:
        return
    AppState.loading_emoji.value = emoji
    AppState.loading_text.value = text


def make_api_request(page, chat_list, user_input, send_btn, text):
    """Blocking API call to run in a background thread."""
    try:
        response = requests.post(
            f"{API_URL}/api/request",
            json={"text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                ui_call(page, add_message, page, chat_list, f"Error: {data['error']}")
            else:
                reply_top = (
                    f"✅ {data.get('status')}\n\n"
                    f"🧑‍🔧 Provider: {data.get('recommended_provider')}"
                )
                reply_bottom = (
                    f"🧠 AI Reasoning:\n{data.get('user_reasoning', '')}\n\n"
                    f"💵 Total Price: {data.get('price_breakdown', {}).get('total')} PKR\n\n"
                    f"⏱️ {data.get('follow_up')}"
                )
                
                async def open_maps(e):
                    await page.launch_url("https://www.google.com/maps/search/?api=1&query=Karachi")

                distance_btn = ft.TextButton(
                    content=ft.Text(f"📍 Distance: {data.get('distance_km')} km"), 
                    on_click=open_maps,
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_900)
                )
                
                async def open_whatsapp(e):
                    await page.launch_url("https://wa.me/923000000000?text=Salam%20Ustaad,%20I%20need%20your%20service%20via%20Ustaad-AI.")

                wa_btn = ft.Button(
                    icon=ft.Icons.CHAT, 
                    content=ft.Text("Message Ustaad on WhatsApp"), 
                    color="white", 
                    bgcolor="green",
                    on_click=open_whatsapp
                )
                
                action_col = ft.Column([
                    distance_btn,
                    ft.Text(reply_bottom, size=15, color=ft.Colors.BLACK87, selectable=True),
                    wa_btn
                ])
                
                ui_call(page, add_message, page, chat_list, reply_top, False, data.get('reasoning'), action_col)
        else:
            ui_call(page, add_message, page, chat_list, "Failed to reach the Ustaad-AI API.")
    except Exception as ex:
        ui_call(page, add_message, page, chat_list, f"Connection Exception: {str(ex)}")
    finally:
        ui_call(page, finish_request_ui, page, chat_list, user_input, send_btn)


def stream_logs(page, log_list):
    """Safe background thread that loops and reconnects to the SSE stream."""
    while True:
        try:
            response = requests.get(
                f"{API_URL}/api/agent-traces",
                stream=True,
                timeout=(SSE_CONNECT_TIMEOUT_SECONDS, SSE_READ_TIMEOUT_SECONDS),
            )
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8', errors='ignore')
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]
                        try:
                            event = json.loads(json_str)
                            step = event.get("step", "log").upper()
                            data = event.get("data", "")
                            
                            if isinstance(data, dict):
                                data_str = json.dumps(data)[:150] + "..." if len(json.dumps(data)) > 150 else json.dumps(data)
                            else:
                                data_str = str(data)[:150]

                            ui_call(page, append_log_entry, page, log_list, step, data_str)
                        except Exception:
                            pass
        except Exception:
            time.sleep(2)


def main(page: ft.Page):
    logo_exists = os.path.exists("assets/logo.png")
    page.title = "Ustaad-AI"
    if logo_exists:
        page.window.icon = "logo.png"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 850
    
    # UI Components
    chat_list = ft.ListView(expand=True, spacing=15, padding=20, auto_scroll=True, scroll=ft.ScrollMode.ALWAYS)
    user_input = ft.TextField(
        hint_text="Mujhe kal subah AC technician chahiye...", 
        expand=True, 
        border_radius=20,
        multiline=False,
    )
    send_btn = ft.IconButton(icon=ft.Icons.SEND, icon_color=ft.Colors.BLUE)
    
    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.Icons.LIGHT_MODE
            theme_btn.icon_color = ft.Colors.WHITE
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.Icons.DARK_MODE
            theme_btn.icon_color = ft.Colors.BLUE_900
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.DARK_MODE,
        icon_color=ft.Colors.BLUE_900,
        on_click=toggle_theme,
        tooltip="Toggle Dark Mode"
    )
    
    async def simulate_voice(e):
        mic_btn.icon_color = "red"
        user_input.hint_text = "🔴 Ustaad-AI sun raha hai... Bolna shuru karein"
        user_input.value = ""
        page.update()
        await asyncio.sleep(3)
        mic_btn.icon_color = "primary"
        user_input.hint_text = "Mujhe kal subah AC technician chahiye..."
        user_input.value = "Malir Halt mein AC theek karwana hai"
        page.update()
        
    mic_btn = ft.IconButton(
        icon=ft.Icons.MIC,
        on_click=lambda e: page.run_task(simulate_voice, e),
        icon_color="primary"
    )
    
    # Header
    header_leading = (
        ft.Image(src="logo.png", width=35, height=35, border_radius=8, fit="contain")
        if logo_exists
        else ft.Icon(ft.Icons.HOME_REPAIR_SERVICE)
    )
    page.appbar = ft.AppBar(
        leading=header_leading,
        title=ft.Text("Ustaad-AI Dashboard", weight="bold"),
        center_title=True,
        bgcolor="surfaceVariant",
        actions=[theme_btn]
    )
    
    # Debug Logs UI
    log_list = ft.ListView(height=150, spacing=5, padding=10, auto_scroll=True)
    log_tile = ft.ExpansionTile(
        title=ft.Text("View AI Agent Reasoning (Debug Traces)", weight="bold", size=14, color="primary"),
        controls=[log_list],
        collapsed_bgcolor="surfaceVariant",
        bgcolor="surfaceVariant"
    )

    def send_click():
        """Event handler for sending messages."""
        text = user_input.value
        if not text.strip():
            return
            
        user_input.value = ""
        add_message(page, chat_list, text, is_user=True)
        user_input.disabled = True
        send_btn.disabled = True
        page.update()
        
        AppState.loading_emoji = ft.Text("🤔", size=14)
        AppState.loading_text = ft.Text("Ustaad-AI soch raha hai...", italic=True, size=14, color="grey700")
        
        loading_content = ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2, color="green700"),
            AppState.loading_emoji,
            AppState.loading_text
        ])

        AppState.loading_bubble = ft.Row([
            ft.Container(content=loading_content, bgcolor="green100", padding=12, border_radius=12, width=280)
        ], alignment=ft.MainAxisAlignment.START)

        chat_list.controls.append(AppState.loading_bubble)
        AppState.loading_active.set()
        page.update()
        
        def animate_loading():
            phrases = [
                ("🤔", "Ustaad-AI soch raha hai..."),
                ("🔍", "Aas paas ustaad dhoond raha hai..."),
                ("💰", "Bhau taal tay kar raha hai..."),
                ("✅", "Booking final kar raha hai...")
            ]
            idx = 0
            while AppState.loading_active.is_set():
                phrase = phrases[idx % len(phrases)]
                ui_call(page, update_loading_ui, phrase[0], phrase[1])
                time.sleep(2.5)
                idx += 1

        threading.Thread(target=animate_loading, daemon=True).start()
        threading.Thread(target=make_api_request, args=(page, chat_list, user_input, send_btn, text), daemon=True).start()

    # Bind event handlers
    user_input.on_submit = lambda _e: send_click()
    send_btn.on_click = lambda _e: send_click()
    
    # Start SSE listener
    threading.Thread(target=stream_logs, args=(page, log_list), daemon=True).start()
    
    # Initial welcome message
    add_message(page, chat_list, "Salam! Mujhe batayein aapko kis Ustaad ki zaroorat hai? (e.g., Electrician, Plumber, AC Technician, Mechanic, Carpenter)", is_user=False)

    # Build page layout
    page.add(
        ft.Column(
            [
                log_tile,
                ft.Container(content=chat_list, expand=True),
                ft.Row([user_input, mic_btn, send_btn])
            ],
            expand=True
        )
    )

if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
