import flet as ft
import requests
import json
import threading
import time
import os
import shutil
import asyncio

# Auto-copy generated logo to assets for the UI
os.makedirs("assets", exist_ok=True)
if not os.path.exists("assets/logo.png"):
    try:
        shutil.copy(r"C:\Users\USER\.gemini\antigravity\brain\2436e616-b771-4a61-a7a2-c813a7f8d024\ustaad_logo_1779057855127.png", "assets/logo.png")
    except Exception:
        pass

API_URL = "http://localhost:8000"

def main(page: ft.Page):
    page.title = "Ustaad-AI"
    page.window.icon = "logo.png"
    page.theme_mode = ft.ThemeMode.LIGHT
    # Enforce mobile-like dimensions
    page.window_width = 450
    page.window_height = 850
    
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
    
    # ---------------------------------------------------
    # UI Components
    # ---------------------------------------------------
    chat_list = ft.ListView(expand=True, spacing=15, padding=20, auto_scroll=True, scroll=ft.ScrollMode.ALWAYS)
    user_input = ft.TextField(
        hint_text="Mujhe kal subah AC technician chahiye...", 
        expand=True, 
        border_radius=20,
        multiline=False,
        on_submit=lambda e: send_click(e) # Bind Enter key correctly
    )
    send_btn = ft.IconButton(
        icon=ft.Icons.SEND, 
        on_click=lambda e: send_click(e), # Bind click correctly
        icon_color=ft.Colors.BLUE
    )
    
    async def simulate_voice(e):
        # 1. Update UI to recording state
        mic_btn.icon_color = "red"
        user_input.hint_text = "🔴 Ustaad-AI sun raha hai... Bolna shuru karein"
        user_input.value = ""
        page.update()

        # 2. Simulated delay
        await asyncio.sleep(3)

        # 3. Reset UI state and dump translated speech text
        mic_btn.icon_color = "primary"
        user_input.hint_text = "Mujhe kal subah AC technician chahiye..."
        user_input.value = "Malir Halt mein AC theek karwana hai"
        page.update()
        
    mic_btn = ft.IconButton(
        icon=ft.Icons.MIC,
        on_click=lambda e: page.run_task(simulate_voice, e),
        icon_color="primary"
    )
    
    # Premium Branding & Header
    page.appbar = ft.AppBar(
        leading=ft.Image(src="logo.png", width=35, height=35, border_radius=8, fit="contain"),
        title=ft.Text("Ustaad-AI Dashboard", weight="bold"),
        center_title=True,
        bgcolor="surfaceVariant",
        actions=[theme_btn]
    )
    
    # AI Thinking Traces (SSE Logs) Window
    log_list = ft.ListView(height=150, spacing=5, padding=10, auto_scroll=True)
    log_tile = ft.ExpansionTile(
        title=ft.Text("View AI Agent Reasoning (Debug Traces)", weight="bold", size=14, color="primary"),
        controls=[log_list],
        collapsed_bgcolor="surfaceVariant",
        bgcolor="surfaceVariant"
    )

    # ---------------------------------------------------
    # Helper Functions
    # ---------------------------------------------------
    loading_bubble = None

    def add_message(text, is_user=False, reasoning_text=None, action_button=None):
        """Adds a chat bubble to the UI"""
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

    def make_api_request(text):
        """Blocking API call to run in a background thread"""
        nonlocal loading_bubble
        try:
            response = requests.post(f"{API_URL}/api/request", json={"text": text})
            
            if loading_bubble in chat_list.controls:
                chat_list.controls.remove(loading_bubble)

            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    add_message(f"Error: {data['error']}")
                else:
                    # Format the final answer nicely
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
                    
                    add_message(reply_top, reasoning_text=data.get('reasoning'), action_button=action_col)
            else:
                add_message("Failed to reach the Ustaad-AI API.")
        except Exception as ex:
            add_message(f"Connection Exception: {str(ex)}")
        finally:
            user_input.disabled = False
            send_btn.disabled = False
            page.update()

    def send_click(e):
        """Properly bound event handler that pushes heavy work to a thread"""
        nonlocal loading_bubble
        text = user_input.value
        if not text.strip():
            return
            
        # Update UI instantly
        user_input.value = ""
        add_message(text, is_user=True)
        user_input.disabled = True
        send_btn.disabled = True
        page.update()
        
        loading_emoji = ft.Text("🤔", size=14)
        loading_text = ft.Text("Ustaad-AI soch raha hai...", italic=True, size=14, color="grey700")
        
        loading_content = ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2, color="green700"),
            loading_emoji,
            loading_text
        ])

        loading_bubble = ft.Row([
            ft.Container(content=loading_content, bgcolor="green100", padding=12, border_radius=12, width=280)
        ], alignment=ft.MainAxisAlignment.START)

        chat_list.controls.append(loading_bubble)
        page.update()
        
        def animate_loading():
            phrases = [
                ("🤔", "Ustaad-AI soch raha hai..."),
                ("🔍", "Aas paas ustaad dhoond raha hai..."),
                ("💰", "Bhau taal tay kar raha hai..."),
                ("✅", "Booking final kar raha hai...")
            ]
            idx = 0
            while loading_bubble in chat_list.controls:
                loading_emoji.value = phrases[idx % len(phrases)][0]
                loading_text.value = phrases[idx % len(phrases)][1]
                try:
                    page.update()
                except Exception:
                    break
                time.sleep(2.5)
                idx += 1

        threading.Thread(target=animate_loading, daemon=True).start()
        
        # Start API request in a safe thread to avoid silent UI blocking/crashing
        threading.Thread(target=make_api_request, args=(text,), daemon=True).start()

    # ---------------------------------------------------
    # Async SSE Background Thread
    # ---------------------------------------------------
    def stream_logs():
        """Safe background thread that loops and reconnects to the SSE stream"""
        while True:
            try:
                response = requests.get(f"{API_URL}/api/agent-traces", stream=True)
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
                                
                                log_list.controls.append(
                                    ft.Text(f"[{step}] {data_str}", size=11, color=ft.Colors.GREY_700, font_family="monospace")
                                )
                                if len(log_list.controls) > 30:
                                    log_list.controls.pop(0)
                            except Exception:
                                pass
                            finally:
                                page.update()
            except Exception:
                time.sleep(2)

    # Launch the SSE listener
    threading.Thread(target=stream_logs, daemon=True).start()

    # ---------------------------------------------------
    # Build Page
    # ---------------------------------------------------
    # Add a welcome message
    add_message("Salam! Mujhe batayein aapko kis Ustaad ki zaroorat hai? (e.g., Electrician, Plumber, AC Technician, Mechanic, Carpenter)", is_user=False)

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
