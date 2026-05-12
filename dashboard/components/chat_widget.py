import json
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_float import float_init
    HAS_FLOAT = True
except ImportError:
    HAS_FLOAT = False

def render_chat_widget(backend_url: str = "http://localhost:8080"):
    """
    Render a pseudo-floating Chatbot widget complying with UI/UX Pro Max standards.
    Mô phỏng Messenger: Icon Avatar ở góc + Popover Window.
    CORS and Backend integration built-in.
    """
    if HAS_FLOAT:
        try:
            float_init()
        except Exception:
            pass # ignore if already init

    # Ensure backend_url does not end with /
    backend_url = backend_url.rstrip('/')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <style>
            /* 
               CRITICAL FIX: Cho phép click xuyên qua iframe xuống dashboard bên dưới
               khi chat panel đang đóng. The elements inside that should be clickable
               must have pointer-events: auto.
            */
            body {{
                        margin: 0; padding: 0;
                        font-family: 'Segoe UI', Inter, Roboto, sans-serif;
                        pointer-events: auto;
                        background: transparent !important;
                    }}
            
            /* -- THE LAUNCHER (Chat Head) -- */
            #chat-launcher {{
                pointer-events: auto; /* Clickable */
                position: fixed; bottom: 20px; right: 20px;
                width: 65px; height: 65px;
                border-radius: 50%;
                box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                cursor: pointer;
                display: flex; justify-content: center; align-items: center;
                z-index: 1000;
                transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                background-color: transparent;
            }}
            #chat-launcher:hover {{
                transform: scale(1.08);
            }}
            #chat-launcher img {{
                width: 100%; height: 100%;
                border-radius: 50%; object-fit: cover;
                border: 3px solid #E5EEF3;
            }}
            #notification-badge {{
                position: absolute; top: 0px; right: 0px;
                background-color: #E63946; color: white;
                font-size: 13px; font-weight: 700;
                border-radius: 12px; padding: 2px 7px;
                display: none;
                border: 2px solid white;
            }}
            
            /* -- THE CHAT PANEL -- */
            #chat-panel {{
                pointer-events: auto; /* Clickable */
                position: fixed; bottom: 100px; right: 20px;
                width: 360px; height: 500px;
                background-color: #FFFFFF;
                border-radius: 16px;
                box-shadow: 0 12px 32px rgba(0,0,0,0.15);
                border: 1px solid #D9E4EC;
                display: flex; flex-direction: column;
                overflow: hidden;
                
                /* Animations */
                opacity: 0;
                transform: scale(0.85) translateY(20px);
                transform-origin: bottom right;
                transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                
                /* Closed state: move it practically out of the way */
                visibility: hidden;
                z-index: 999;
            }}
            #chat-panel.open {{
                opacity: 1;
                transform: scale(1) translateY(0);
                visibility: visible;
            }}
            
            /* -- Header -- */
            #chat-header {{
                background: linear-gradient(135deg, #16324F 0%, #2B7BBB 100%);
                color: white;
                padding: 16px;
                display: flex; align-items: center; justify-content: space-between;
                border-bottom: 2px solid #D9E4EC;
            }}
            #chat-header-info {{
                display: flex; align-items: center; gap: 12px;
            }}
            #chat-header-info img {{
                width: 38px; height: 38px; border-radius: 50%;
                border: 2px solid rgba(255,255,255,0.8);
            }}
            .status-dot {{
                width: 10px; height: 10px; background-color: #22C55E;
                border-radius: 50%; display: inline-block;
                box-shadow: 0 0 0 2px rgba(34,197,94,0.3);
            }}
            
            /* Action Buttons in Header */
            .header-actions {{ display: flex; gap: 8px; }}
            .header-btn {{
                background: rgba(255,255,255,0.2); border: none; color: white;
                width: 28px; height: 28px; border-radius: 50%;
                cursor: pointer; display: flex; align-items: center; justify-content: center;
                transition: background 0.2s;
            }}
            .header-btn:hover {{ background: rgba(255,255,255,0.4); }}
            
            /* -- Messages Area -- */
            #chat-messages {{
                flex: 1; overflow-y: auto; padding: 18px;
                display: flex; flex-direction: column; gap: 12px;
                background-color: #F4F8FB;
                scrollbar-width: thin;
            }}
            #chat-messages::-webkit-scrollbar {{ width: 6px; }}
            #chat-messages::-webkit-scrollbar-thumb {{ background: #D9E4EC; border-radius: 4px; }}
            
            /* Msg bubbles */
            .msg-bubble {{
                max-width: 82%; padding: 12px 16px;
                font-size: 14.5px; line-height: 1.5; word-wrap: break-word;
                animation: fadeIn 0.3s ease-out;
            }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            
            .msg-user {{
                align-self: flex-end;
                background: linear-gradient(135deg, #2B7BBB 0%, #1E88E5 100%); 
                color: white;
                border-radius: 18px 18px 2px 18px;
                box-shadow: 0 2px 6px rgba(43,123,187,0.2);
            }}
            .msg-bot {{
                align-self: flex-start;
                background-color: #FFFFFF; color: #16324F;
                border: 1px solid #D9E4EC;
                border-radius: 18px 18px 18px 2px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            }}
            .msg-bot pre {{
                background-color: #16324F; color: #E5EEF3;
                padding: 10px; border-radius: 8px; overflow-x: auto;
                font-size: 13px; margin: 8px 0;
            }}
            .msg-bot code {{ font-family: 'Consolas', 'Courier New', monospace; }}
            
            /* -- Input Area -- */
            #chat-input-area {{
                display: flex; align-items: flex-end;
                padding: 14px; border-top: 1px solid #D9E4EC;
                background: #FFFFFF; gap: 10px;
            }}
            #chat-textarea {{
                flex: 1; border: 1px solid #D9E4EC; border-radius: 20px;
                padding: 10px 14px; font-family: inherit; font-size: 14px;
                outline: none; resize: none; min-height: 20px; max-height: 120px;
                background-color: #F4F8FB; transition: border 0.3s;
                overflow-y: auto;
            }}
            #chat-textarea:focus {{ border-color: #2B7BBB; background-color: #FFF; }}
            
            #btn-send {{
                background-color: #2B7BBB; color: white;
                border: none; border-radius: 50%;
                width: 42px; height: 40px; cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                transition: background 0.2s, transform 0.2s;
                flex-shrink: 0; margin-bottom: 2px;
            }}
            #btn-send:hover {{ background-color: #1E88E5; transform: scale(1.05); }}
            #btn-send:disabled {{ background-color: #D9E4EC; cursor: not-allowed; transform: scale(1); }}
            #btn-send svg {{ fill: white; width: 18px; }}
            
            /* -- Interactive Cards -- */
            .approval-card {{
                background: #FFF9E6; border: 1px solid #FFCC00; border-radius: 10px;
                padding: 14px; margin-top: 12px; font-size: 14px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.03);
            }}
            .card-title {{ font-weight: 700; color: #856404; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }}
            .card-actions {{ display: flex; gap: 8px; margin-top: 12px; }}
            
            .approve-btn {{
                flex: 1; background: #22C55E; color: white; font-weight: 600;
                border: none; padding: 8px; border-radius: 8px; cursor: pointer;
                transition: opacity 0.2s;
            }}
            .reject-btn {{
                flex: 1; background: #E63946; color: white; font-weight: 600;
                border: none; padding: 8px; border-radius: 8px; cursor: pointer;
                transition: opacity 0.2s;
            }}
            .approve-btn:hover, .reject-btn:hover {{ opacity: 0.85; }}
            
            .chat-chart-container {{
                margin-top: 10px; text-align: center;
            }}
            .chat-chart-iframe {{
                width: 100%; height: 260px; border: none; border-radius: 8px;
                pointer-events: auto; /* allow clicking the iframe preview */
            }}

            /* -- Chart thumbnail wrapper -- */
            .chat-chart-thumb {{
                position: relative; margin-top: 10px; cursor: pointer;
                border: 1px solid #D9E4EC; border-radius: 8px; overflow: hidden;
            }}
            .chat-chart-overlay {{
                position: absolute; inset: 0;
                background: rgba(22, 50, 79, 0.0);
                display: flex; align-items: center; justify-content: center;
                transition: background 0.25s;
            }}
            .chat-chart-thumb:hover .chat-chart-overlay {{
                background: rgba(22, 50, 79, 0.45);
            }}
            .btn-view-full {{
                opacity: 0; transform: scale(0.85);
                transition: opacity 0.25s, transform 0.25s;
                background: #2B7BBB; color: white; border: none;
                padding: 8px 18px; border-radius: 20px; font-size: 13px;
                font-weight: 600; cursor: pointer; pointer-events: none;
            }}
            .chat-chart-thumb:hover .btn-view-full {{
                opacity: 1; transform: scale(1);
            }}

            /* Ensure the widget iframe placed by Streamlit accepts pointer events */
            iframe[title="st.iframe"] {{ pointer-events: auto !important; z-index: 2000 !important; }}

            /* -- Viewer Modal -- */
            #viewer-modal-overlay {{
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.75); z-index: 3000;
                display: none; align-items: center; justify-content: center;
                backdrop-filter: blur(4px);
                pointer-events: auto;
            }}
            #viewer-modal {{
                background: #1E1E1E; width: 92vw; height: 90vh;
                border-radius: 12px; display: flex; flex-direction: column;
                box-shadow: 0 24px 64px rgba(0,0,0,0.6); overflow: hidden;
                border: 1px solid #454545;
                animation: scaleUp 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }}
            #viewer-modal-header {{
                background: #323233; height: 42px; display: flex; align-items: center;
                justify-content: space-between; padding: 0 18px;
                color: #CCCCCC; font-size: 14px; font-weight: 500; flex-shrink: 0;
                border-bottom: 1px solid #454545;
            }}
            #viewer-modal-body {{
                flex: 1; overflow: hidden; background: #fff;
            }}
            #viewer-modal-body iframe {{
                width: 100%; height: 100%; border: none;
            }}
            #viewer-modal-body img {{
                width: 100%; height: 100%; object-fit: contain; background: #fff;
            }}
            
            /* -- Typing animation -- */
            .typing-indicator {{ display: flex; align-items: center; gap: 4px; padding: 14px 20px; }}
            .typing-indicator span {{
                display: inline-block; width: 6px; height: 6px; background-color: #4F6B7A;
                border-radius: 50%; opacity: 0.4;
                animation: pulse 1.2s infinite cubic-bezier(0.2, 0.68, 0.18, 1.08);
            }}
            .typing-indicator span:nth-child(2) {{ animation-delay: 0.2s; }}
            .typing-indicator span:nth-child(3) {{ animation-delay: 0.4s; }}
            @keyframes pulse {{ 0%, 100% {{transform:scale(1); opacity:0.4;}} 50% {{transform:scale(1.3); opacity:1;}} }}
            
            /* -- VS Code Editor Modal -- */
            #code-modal-overlay {{
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0, 0, 0, 0.5); z-index: 2000;
                display: none; align-items: center; justify-content: center;
                backdrop-filter: blur(3px);
                pointer-events: auto;
            }}
            #code-modal {{
                background: #1E1E1E; width: 95%; height: 92%;
                border-radius: 8px; display: flex; flex-direction: column;
                box-shadow: 0 24px 48px rgba(0,0,0,0.5); overflow: hidden;
                border: 1px solid #454545;
                animation: scaleUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            @keyframes scaleUp {{ from {{ transform: scale(0.95); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
            
            /* VS Code Title bar */
            #vscode-titlebar {{
                background: #323233; height: 35px; display: flex; align-items: center; justify-content: space-between;
                padding: 0 15px; color: #CCCCCC; font-size: 13px; user-select: none; flex-shrink: 0;
            }}
            .vscode-mac-btns {{ display: flex; gap: 8px; }}
            .vscode-mac-btns span {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; cursor: pointer; }}
            .mac-close {{ background: #FF5F56; }}
            .mac-min {{ background: #FFBD2E; }}
            .mac-max {{ background: #27C93F; }}
            
            #vscode-body {{ display: flex; flex: 1; overflow: hidden; }}
            
            /* VS Code Sidebar */
            #vscode-sidebar {{ width: 50px; background: #333333; display: flex; flex-direction: column; align-items: center; padding-top: 15px; gap: 20px; border-right: 1px solid #252526; flex-shrink: 0; }}
            .sidebar-icon {{ width: 24px; height: 24px; opacity: 0.5; cursor: pointer; transition: opacity 0.2s; }}
            .sidebar-icon:hover {{ opacity: 1; }}
            .sidebar-icon.active {{ opacity: 1; position: relative; }}
            .sidebar-icon.active::before {{ content: ''; position: absolute; left: -13px; top: 0; bottom: 0; width: 2px; background: #007ACC; }}
            
            /* VS Code Editor Area */
            #vscode-editor-container {{ flex: 1; display: flex; flex-direction: column; background: #1E1E1E; position: relative; }}
            #vscode-tabs {{ display: flex; background: #252526; height: 35px; flex-shrink: 0; }}
            .vscode-tab {{ background: #1E1E1E; color: #9CDCFE; padding: 0 20px; display: flex; align-items: center; font-size: 13px; border-top: 1px solid #007ACC; gap: 8px; cursor: default; }}
            
            #code-textarea {{
                flex: 1; border: none; background: #1E1E1E; color: #D4D4D4;
                font-family: 'Consolas', 'Courier New', monospace; font-size: 14.5px;
                padding: 16px 20px; margin: 0; outline: none; resize: none; line-height: 1.6;
                tab-size: 4; white-space: pre; overflow: auto;
            }}
            #code-textarea::-webkit-scrollbar {{ width: 12px; height: 12px; }}
            #code-textarea::-webkit-scrollbar-corner {{ background: #1E1E1E; }}
            #code-textarea::-webkit-scrollbar-thumb {{ background: #424242; border: 3px solid #1E1E1E; border-radius: 6px; }}
            #code-textarea::-webkit-scrollbar-thumb:hover {{ background: #4F4F4F; }}
            
            /* VS Code Status bar */
            #vscode-statusbar {{
                height: 22px; background: #007ACC; color: white; display: flex; align-items: center; justify-content: space-between;
                padding: 0 10px; font-size: 12px; flex-shrink: 0;
            }}
            .statusbar-left, .statusbar-right {{ display: flex; align-items: center; gap: 15px; }}
            .statusbar-right {{ display: flex; align-items: center; gap: 10px; margin-right: 10px; }}
            
            .run-button {{
                background: #238636; border: 1px solid rgba(255,255,255,0.1); color: white; border-radius: 4px; padding: 2px 14px;
                font-size: 12px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 5px; height: 26px; transition: 0.2s;
            }}
            .run-button:hover {{ background: #2EA043; }}

        </style>
    </head>
    
    <body>

        <!-- Launcher -->
        <div id="chat-launcher" onclick="toggleChat()">
            <img src="https://ui-avatars.com/api/?name=AI&background=16324F&color=fff&size=100&font-size=0.4" alt="Avatar" />
            <div id="notification-badge">0</div>
        </div>

        <!-- Panel -->
        <div id="chat-panel">
            <div id="chat-header">
                <div id="chat-header-info">
                    <img src="https://ui-avatars.com/api/?name=AI&background=FFF&color=16324F&size=100" alt="Bot" />
                    <div>
                        <div style="font-weight: 600; font-size: 15px;">Air Quality AI</div>
                        <div style="font-size: 12px; color: #D9E4EC; display: flex; align-items: center; gap: 4px; margin-top: 2px;">
                            <span class="status-dot"></span> Đang trực tuyến
                        </div>
                    </div>
                </div>
                <div class="header-actions">
                    <button class="header-btn" onclick="toggleChat()"> <!-- Minimize -->
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M19 12H5"></path></svg>
                    </button>
                </div>
            </div>
            
            <div id="chat-messages">
                <!-- Data injection point -->
            </div>
            
            <div id="chat-input-area">
                <textarea id="chat-textarea" rows="1" placeholder="Nhập câu hỏi tại đây..."></textarea>
                <button id="btn-send" onclick="sendPrompt()" title="Gửi">
                    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
                </button>
            </div>
            
            <!-- Code Editor Modal — outside chat-panel to avoid clipping -->
        </div> <!-- end #chat-panel -->

        <!-- Code Editor Modal -->
        <div id="code-modal-overlay">
            <div id="code-modal">
                    <!-- Title Bar -->
                    <div id="vscode-titlebar">
                        <div class="vscode-mac-btns">
                            <span class="mac-close" onclick="closeCodeModal()" title="Đóng"></span>
                            <span class="mac-min" onclick="closeCodeModal()"></span>
                            <span class="mac-max"></span>
                        </div>
                        <div style="font-weight: 500;">analysis_script.py - Visual Studio Code</div>
                        <div style="width: 44px;"></div> <!-- Spacer -->
                    </div>
                    
                    <!-- Middle Body -->
                    <div id="vscode-body">
                        <!-- Left Sidebar -->
                        <div id="vscode-sidebar">
                            <svg class="sidebar-icon active" viewBox="0 0 24 24"><path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2m0 16H5V5h14v14z"></path><path fill="currentColor" d="M7 12h10v2H7zm0-4h10v2H7zm0 8h7v2H7z"></path></svg>
                            <svg class="sidebar-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"></path></svg>
                        </div>
                        
                        <!-- Editor Container -->
                        <div id="vscode-editor-container">
                            <!-- Tabs -->
                            <div id="vscode-tabs">
                                <div class="vscode-tab">
                                    <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2m0 16H5V5h14v14z"></path><path fill="#FFD700" d="M14 17l-4-4 4-4v8z"></path></svg>
                                    analysis_script.py
                                </div>
                                <div style="flex:1; display:flex; justify-content: flex-end; align-items:center; padding-right:15px;">
                                    <button class="run-button" id="btn-run-code" onclick="runCodeFromEditor()">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                        Run Python
                                    </button>
                                </div>
                            </div>
                            <!-- Textarea -->
                            <textarea id="code-textarea" spellcheck="false"></textarea>
                        </div>
                    </div>
                    
                    <!-- Status Bar -->
                    <div id="vscode-statusbar">
                        <div class="statusbar-left">
                            <span><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" style="vertical-align:middle; margin-right:4px;"><path d="M11 11V5h-2v6h2zm1-9H4C2.9 2 2 2.9 2 4v8c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m0 10H4V4h8v8z"></path></svg> master*</span>
                            <span>UTF-8</span>
                            <span>Python 3.12</span>
                        </div>
                        <div class="statusbar-right">
                            <span>Ln 1, Col 1</span>
                            <span>Spaces: 4</span>
                        </div>
                    </div>
                </div>
            </div>

        <!-- Viewer Modal -->
        <div id="viewer-modal-overlay" onclick="handleViewerOverlayClick(event)">
            <div id="viewer-modal">
                <div id="viewer-modal-header">
                    <span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:-4px; margin-right:6px;"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle></svg> Trình xem Biểu đồ</span>
                    <div style="cursor:pointer; color:#9CDCFE; transition: 0.2s;" onclick="closeViewerModal()" title="Đóng (Esc)">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"></path></svg>
                    </div>
                </div>
                <div id="viewer-modal-body"></div>
            </div>
        </div>

        <script>
            // Setup endpoints
            const BACKEND_URL = "{backend_url}";
            
            // State
            let isChatOpen = false;
            let unreadCount = 0;
            let currentChatHistory = [];
            let codesMap = {{}}; // Maps chat_id -> base64/raw code for execution. But wait, execute only needs chat_id if code implies server pulls it? 
            // In backend/main.py, ExecuteRequest needs BOTH code and chat_id! We must store the returned code.
            
            // Load state
            const savedHistory = sessionStorage.getItem('ai_chat_history');
            const savedCodes = sessionStorage.getItem('ai_chat_codes');
            
            const messagesDiv = document.getElementById('chat-messages');

            if (savedHistory) {{
                currentChatHistory = JSON.parse(savedHistory);
                if (savedCodes) codesMap = JSON.parse(savedCodes);
                renderAllMessages();
            }} else {{
                // Initial message
                const msg = "Xin chào! Trợ lý AI phân tích dữ liệu không khí TPHCM sẵn sàng. Bạn muốn phân tích hay yêu cầu vẽ biểu đồ gì?";
                currentChatHistory.push({{ role: 'assistant', content: msg, rendered_html: `<div class="msg-bubble msg-bot">${{msg}}</div>` }});
                saveState();
                renderAllMessages();
            }}

            function saveState() {{
                sessionStorage.setItem('ai_chat_history', JSON.stringify(currentChatHistory));
                sessionStorage.setItem('ai_chat_codes', JSON.stringify(codesMap));
            }}

            function toggleChat() {{
                const panel = document.getElementById('chat-panel');
                isChatOpen = !isChatOpen;
                if (isChatOpen) {{
                    panel.classList.add('open');
                    document.getElementById('notification-badge').style.display = 'none';
                    unreadCount = 0;
                    setTimeout(() => document.getElementById('chat-textarea').focus(), 300);
                    resizeHostIframe(true);
                }} else {{
                    panel.classList.remove('open');
                    // Đợi animation đóng xong (300ms) rồi mới shrink iframe
                    setTimeout(() => resizeHostIframe(false), 320);
                }}
            }}

            // Resize iframe chứa widget từ bên trong.
            // window.frameElement trỏ trực tiếp đến <iframe> element ở parent DOM.
            function resizeHostIframe(open) {{
                try {{
                    const frame = window.frameElement;
                    if (!frame) return;
                    if (open) {{
                        frame.style.width  = '420px';
                        frame.style.height = '660px';
                    }} else {{
                        frame.style.width  = '90px';
                        frame.style.height = '90px';
                    }}
                }} catch(e) {{
                    // Cross-origin block — fallback: không làm gì, iframe giữ nguyên
                }}
            }}

            // Shrink ngay khi load trang (chat chưa mở)
            resizeHostIframe(false);

            function updateBadge() {{
                if (!isChatOpen) {{
                    unreadCount++;
                    const badge = document.getElementById('notification-badge');
                    badge.innerText = unreadCount > 9 ? '9+' : unreadCount;
                    badge.style.display = 'block';
                }}
            }}

            // Input behavior
            const textarea = document.getElementById('chat-textarea');
            textarea.addEventListener('input', function() {{
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight < 120 ? this.scrollHeight : 120) + 'px';
            }});
            textarea.addEventListener('keypress', function(e) {{
                if (e.key === 'Enter' && !e.shiftKey) {{
                    e.preventDefault();
                    sendPrompt();
                }}
            }});

            function appendToDOM(htmlStr) {{
                messagesDiv.insertAdjacentHTML('beforeend', htmlStr);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}

            function addUserMessage(text) {{
                const html = `<div class="msg-bubble msg-user">${{escapeHTML(text).replace(/\\n/g, '<br>')}}</div>`;
                currentChatHistory.push({{role: "user", content: text, rendered_html: html}});
                saveState();
                appendToDOM(html);
            }}

            function addBotMessage(text, htmlContent = null) {{
                const finalHTML = htmlContent || `<div class="msg-bubble msg-bot">${{escapeHTML(text).replace(/\\n/g, '<br>')}}</div>`;
                currentChatHistory.push({{role: "assistant", content: text, rendered_html: finalHTML}});
                saveState();
                appendToDOM(finalHTML);
                updateBadge();
            }}

            function addTypingIndicator() {{
                const id = 'typing-' + Date.now();
                appendToDOM(`
                    <div id="${{id}}" class="msg-bubble msg-bot typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                `);
                return id;
            }}

            function removeElement(id) {{
                const el = document.getElementById(id);
                if (el) el.remove();
            }}

            function escapeHTML(str) {{
                return str.replace(/[&<>'"]/g, 
                    tag => ({{
                        '&': '&amp;',
                        '<': '&lt;',
                        '>': '&gt;',
                        "'": '&#39;',
                        '"': '&quot;'
                    }}[tag]));
            }}

            async function sendPrompt() {{
                const prompt = textarea.value.trim();
                if (!prompt) return;
                
                textarea.value = ''; textarea.style.height = 'auto';
                document.getElementById('btn-send').disabled = true;
                
                addUserMessage(prompt);
                const typingId = addTypingIndicator();

                try {{
                    // Lọc lịch sử hợp lệ để gửi backend API (chỉ gửi prompt user và text bot)
                    const payloadHistory = currentChatHistory.slice(0, -1).map(x => ({{
                        role: x.role,
                        content: x.content
                    }}));
                    
                    const reqBody = {{
                        "prompt": prompt,
                        "context": "",
                        "history": payloadHistory
                    }};
                    
                    const response = await fetch(`${{BACKEND_URL}}/api/chat`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(reqBody)
                    }});
                    
                    removeElement(typingId);
                    
                    if (!response.ok) {{
                        const errText = await response.text();
                        addBotMessage(`Lỗi Server (${{response.status}}): ${{errText}}`);
                        return;
                    }}
                    
                    const data = await response.json(); // {{"chat_id", "code", "explanation"}}
                    
                    let botMsgText = data.explanation || "✅ Đã tạo xong kế hoạch và mã nguồn.";
                    let finalHTML = `<div class="msg-bubble msg-bot">`;
                    finalHTML += `<div>${{escapeHTML(botMsgText).replace(/\\n/g, '<br>')}}</div>`;
                    
                    if (data.code && data.chat_id) {{
                        // Store code to trigger execute later
                        codesMap[data.chat_id] = data.code;
                        const cardId = 'approve-' + data.chat_id;
                        
                        finalHTML += `
                            <div class="approval-card" id="${{cardId}}">
                                <div class="card-title">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                                    Yêu cầu phê duyệt
                                </div>
                                <div style="color:#57534E;">Mã phân tích dữ liệu đã được tạo. Vui lòng duyệt để chạy kết quả.</div>
                                <div class="card-actions" style="flex-direction: column;">
                                    <button class="approve-btn" style="display:flex; justify-content:center; align-items:center; gap:6px;" onclick="openCodeModal('${{data.chat_id}}', '${{cardId}}')">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                                        Xem & Chỉnh sửa Mã (Review)
                                    </button>
                                    <button class="reject-btn" onclick="rejectCode('${{cardId}}')">❌ Bỏ Qua</button>
                                </div>
                            </div>
                        `;
                    }}
                    finalHTML += `</div>`;
                    
                    addBotMessage(botMsgText, finalHTML);

                }} catch (error) {{
                    removeElement(typingId);
                    addBotMessage("Lỗi không mong muốn: " + error.message);
                }} finally {{
                    document.getElementById('btn-send').disabled = false;
                }}
            }}

            window.rejectCode = function(cardId) {{
                const card = document.getElementById(cardId);
                if (card) {{
                    card.innerHTML = `<div style="color: #E63946; font-style: italic; font-weight: 500;">❌ Đã hủy yêu cầu sinh biểu đồ.</div>`;
                    updateHTMLInHistory(cardId, card.innerHTML);
                }}
            }};
            
            // --- Code Editor Logic ---
            let currentEditingChatId = null;
            let currentEditingCardId = null;

            // --- Fullscreen Expansion Logic ---
            function setIframeFullscreen(isFullscreen, elementId = 'code-modal') {{
                try {{
                    const el = document.getElementById(elementId);
                    if (isFullscreen && el) {{
                        if (el.requestFullscreen) {{
                            el.requestFullscreen().catch(e => console.log(e));
                        }} else if (el.webkitRequestFullscreen) {{
                            el.webkitRequestFullscreen();
                        }} else if (el.msRequestFullscreen) {{
                            el.msRequestFullscreen();
                        }}
                        
                        // Fallback fallback: phóng to CSS overlay tĩnh bên trong iframe đề phòng Fullscreen bị chặn
                        el.style.width = '100vw';
                        el.style.height = '100vh';
                        el.style.borderRadius = '0';
                    }} else {{
                        if (document.fullscreenElement || document.webkitFullscreenElement) {{
                            if (document.exitFullscreen) {{
                                document.exitFullscreen().catch(e => console.log(e));
                            }} else if (document.webkitExitFullscreen) {{
                                document.webkitExitFullscreen();
                            }}
                        }}
                        
                        // Phục hồi CSS tĩnh
                        if (el) {{
                            el.style.width = elementId === 'code-modal' ? '95%' : '92vw';
                            el.style.height = elementId === 'code-modal' ? '92%' : '90vh';
                            el.style.borderRadius = elementId === 'code-modal' ? '8px' : '12px';
                        }}
                    }}
                }} catch(e) {{
                    console.log("Fullscreen API error", e);
                }}
            }}

            window.openCodeModal = function(chatId, cardId) {{
                currentEditingChatId = chatId;
                currentEditingCardId = cardId;
                const codeStr = codesMap[chatId] || "";
                document.getElementById('code-textarea').value = codeStr;
                document.getElementById('code-modal-overlay').style.display = 'flex';
                setIframeFullscreen(true, 'code-modal');
            }};

            window.closeCodeModal = function() {{
                document.getElementById('code-modal-overlay').style.display = 'none';
                currentEditingChatId = null;
                currentEditingCardId = null;
                setIframeFullscreen(false, 'code-modal');
            }};

            window.runCodeFromEditor = function() {{
                if (currentEditingChatId && currentEditingCardId) {{
                    // Capture IDs before closing modal because closeCodeModal() clears them
                    const chatIdToRun = currentEditingChatId;
                    const cardIdToRun = currentEditingCardId;
                    codesMap[chatIdToRun] = document.getElementById('code-textarea').value;
                    saveState();
                    closeCodeModal();
                    executeCode(chatIdToRun, cardIdToRun);
                }}
            }};
            // -------------------------

            // --- Viewer Modal Logic ---
            window.openViewerModal = function(url, type) {{
                const overlay = document.getElementById('viewer-modal-overlay');
                const body = document.getElementById('viewer-modal-body');
                if (type === 'html') {{
                    body.innerHTML = `<iframe src="${{url}}" allowfullscreen></iframe>`;
                }} else {{
                    body.innerHTML = `<img src="${{url}}" alt="chart" />`;
                }}
                overlay.style.display = 'flex';
                setIframeFullscreen(true, 'viewer-modal');
            }};

            window.closeViewerModal = function() {{
                document.getElementById('viewer-modal-overlay').style.display = 'none';
                document.getElementById('viewer-modal-body').innerHTML = '';
                setIframeFullscreen(false, 'viewer-modal');
            }};

            window.handleViewerOverlayClick = function(e) {{
                // Close when clicking the dark backdrop (not the modal itself)
                if (e.target === document.getElementById('viewer-modal-overlay')) {{
                    closeViewerModal();
                }}
            }};

            // Close viewer on Esc key
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') {{
                    closeViewerModal();
                    closeCodeModal();
                }}
            }});

            window.executeCode = async function(chatId, cardId) {{
                const card = document.getElementById(cardId);
                const codeStr = codesMap[chatId];
                
                if (!codeStr) {{
                    card.innerHTML = `<div style="color:red">Lỗi: Mất mã nguồn trong bộ nhớ tạm. Vui lòng load lại trang.</div>`;
                    return;
                }}

                if (card) card.innerHTML = `
                    <div style="display: flex; align-items: center; color: #2B7BBB; font-weight: 500;">
                        <span style="font-size: 16px; margin-right: 6px;" class="spinning">⚙️</span> Đang biểu diễn phân tích...
                    </div>
                    <style>.spinning {{ display: inline-block; animation: spin 2s linear infinite; }} @keyframes spin {{ 100% {{transform: rotate(360deg);}} }} </style>
                `;

                try {{
                    const response = await fetch(`${{BACKEND_URL}}/api/execute`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ "code": codeStr, "chat_id": chatId }})
                    }});
                    
                    const resData = await response.json();
                    
                    if (!response.ok) {{
                        card.innerHTML = `<div style="color: #E63946;"><b>Thất bại:</b> ${{resData.detail || "Không rõ."}}</div>`;
                        return;
                    }}
                    
                    if (resData.success) {{
                        let content = `<div style="color: #22C55E; font-weight: bold; margin-bottom: 8px;">✅ Chạy thành công.</div>`;
                        if (resData.chart_url) {{
                            const fullUrl = `${{BACKEND_URL}}${{resData.chart_url}}`;
                            const bustUrl = fullUrl + "?t=" + Date.now();
                            if (resData.chart_url.endsWith('.html')) {{
                                content += `
                                <div class="chat-chart-thumb" onclick="openViewerModal('${{bustUrl}}', 'html')">
                                    <iframe src="${{bustUrl}}" class="chat-chart-iframe"></iframe>
                                    <div class="chat-chart-overlay"><button class="btn-view-full">🔍 Xem toàn màn</button></div>
                                </div>`;
                            }} else {{
                                content += `
                                <div class="chat-chart-thumb" onclick="openViewerModal('${{bustUrl}}', 'img')">
                                    <img src="${{bustUrl}}" class="chat-chart-iframe" style="object-fit: contain; background: white;"/>
                                    <div class="chat-chart-overlay"><button class="btn-view-full">🔍 Xem toàn màn</button></div>
                                </div>`;
                            }}
                        }} else if (resData.stdout) {{
                            content += `<pre style="font-size:12px; background:#F4F8FB; padding:8px; border:1px solid #D9E4EC; color:#16324F;">${{escapeHTML(resData.stdout)}}</pre>`;
                        }}
                        card.innerHTML = content;
                        
                    }} else {{
                        card.innerHTML = `<div style="color: #E63946;"><b>Lỗi Code:</b><br><pre style="white-space:pre-wrap;font-size:11px;">${{escapeHTML(resData.stderr || resData.stdout)}}</pre></div>`;
                    }}
                    
                    updateHTMLInHistory(cardId, card.innerHTML);
                    
                }} catch (e) {{
                    card.innerHTML = `<div style="color: #E63946;">Lỗi mạng trong lúc chạy: ${{e.message}}</div>`;
                }}
            }};

            // Thay thế nội dung HTML cũ trong currentChatHistory khi user click Duyệt / Bỏ Qua
            function updateHTMLInHistory(cardId, newCardHTML) {{
                // Tim msg co id kia, the cardId is embedded within rendered_html
                for (let i = currentChatHistory.length - 1; i >= 0; i--) {{
                    if (currentChatHistory[i].rendered_html.includes(cardId)) {{
                        // Dùng DOMParser để thay phần div đó. Nhưng Regex dễ hơn.
                        const regex = new RegExp(`<div class="approval-card"[^>]*id="${{cardId}}"[^>]*>.*?</div><!--end-->|<div class="approval-card" id="${{cardId}}">[\\s\\S]*?</div>`, "g");
                        currentChatHistory[i].rendered_html = currentChatHistory[i].rendered_html.replace(regex, `<div class="approval-card" id="${{cardId}}">${{newCardHTML}}</div>`);
                        saveState();
                        break;
                    }}
                }}
            }}

            function renderAllMessages() {{
                messagesDiv.innerHTML = '';
                currentChatHistory.forEach(msg => {{
                    appendToDOM(msg.rendered_html);
                }});
                // Scroll to bottom
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}
        </script>
    </body>
    </html>
    """
    
    # ── RENDER COMPONENT ──
    container = st.container()
    with container:
        # Bắt đầu nhỏ (90px = launcher only).
        # Script bên trong iframe sẽ tự resize qua window.frameElement khi chat mở/đóng.
        components.html(html_content, height=90)

    # Chỉ cần cố định vị trí iframe — width/height do script bên trong tự quản lý.
    st.markdown(
        """
        <style>
            iframe[title="st.iframe"] {
                position: fixed !important;
                right: 20px !important;
                bottom: 20px !important;
                z-index: 99999 !important;
                border: none !important;
                transition: width 0.2s ease, height 0.2s ease !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
