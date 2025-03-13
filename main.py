import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from flask_session import Session
from openai import OpenAI
from functools import wraps
import json

# 加載環境變量
load_dotenv()

# 環境變量
NICK = os.getenv('NICK')
VINAY_PASSWORD = os.getenv('VINAY')
TAKESHI_PASSWORD = os.getenv('TAKESHI')
NOBODY_PASSWORD = os.getenv('NOBODY')

# 添加模型配置
MODEL_CONFIGS = {
    'gpt-4o-mini': {
        'model': 'gpt-4o-mini',
        'messages': [],
        'response_format': {
            'type': 'text'
        },
        'temperature': 0.8,
        'max_completion_tokens': 10240
    },
    'o3-mini': {
        'model': 'o3-mini',
        'messages': [],
        'response_format': {
            'type': 'text'
        },
        'reasoning_effort': 'medium'
    }
}

# 初始化Flask應用
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config.update({
    'SESSION_TYPE': 'filesystem',
    
    'SESSION_COOKIE_SECURE': False,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_PERMANENT': True,
    'PERMANENT_SESSION_LIFETIME': timedelta(hours=8),
    'SESSION_REFRESH_EACH_REQUEST': False
})
Session(app)

# 初始化全局OpenAI客戶端
client = OpenAI()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == VINAY_PASSWORD:
            return login_user('vinay')
        elif password == TAKESHI_PASSWORD:
            return login_user('takeshi')
        elif password == NOBODY_PASSWORD:
            return login_user('nobody')
        else:
            return render_template('login.html', error='密碼無效')
    return render_template('login.html')

def login_user(user_type):
    session.permanent = True
    session['logged_in'] = True
    session['user_type'] = user_type  # 存儲用戶類型到session
    session['history'] = []
    session['messages'] = initialize_message(user_type)
    return redirect(url_for('chat'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('messages', None)
    session.pop('history', None)
    session.pop('user_type', None)
    return redirect(url_for('login'))

# 定義模板名稱
chat_templates = {
    'vinay': 'chat_queen.html',
    'takeshi': 'chat_takeshi.html',
    'nobody': 'chat_nobody.html'
}

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user_type = session.get('user_type')
    template = chat_templates.get(user_type)
    if not template:
        return redirect(url_for('login'))

    current_model = session.get('current_model', 'gpt-4o-mini')

    if request.method == "POST":
        try:
            user_input = request.form.get("user_input")
            if not user_input:
                return jsonify({'error': '請輸入問題'})

            model_name = request.form.get("model", current_model)
            
            # 检查是否为AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # 只返回流式处理所需的信息
                session['current_model'] = model_name
                session['messages'].append({"role": "user", "content": user_input})
                return jsonify({
                    'success': True,
                    'message_id': len(session['history']),
                    'user_input': user_input
                })
            else:
                # 非AJAX请求处理（降级方案）
                response, messages = get_openai_response(user_input, session['messages'], model_name)
                session['history'].append({"user": user_input, "assistant": response})
                session['messages'] = messages
                session['current_model'] = model_name
                return redirect(url_for('chat'))

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'error': str(e),
                    'success': False
                })
            else:
                # 如果是普通表單提交，重定向回聊天頁面
                return redirect(url_for('chat'))

    # GET 請求顯示聊天頁面
    return render_template(template, 
                         history=session.get('history', []), 
                         NICK=NICK,
                         current_model=current_model)

@app.route("/stream_response")
@login_required
def stream_response():
    """處理OpenAI API流式輸出的路由"""
    # 在進入生成器前預先獲取會話數據
    if not session.get('messages'):
        return Response("data: " + json.dumps({"error": "無效的會話狀態"}) + "\n\n", 
                       content_type='text/event-stream')
    
    # 獲取會話中的所有數據並創建本地副本
    messages = session.get('messages', [])[:]  # 創建副本
    model_name = session.get('current_model', 'gpt-4o-mini')
    session_id = session.get('_id')  # 獲取會話ID用於後續更新
    
    def generate():
        """生成器函數不再存取session對象"""
        try:
            model_config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS['gpt-4o-mini'])
            full_response = ""
            
            # 根據不同模型使用不同的配置
            if model_name == 'o3-mini':
                stream = client.chat.completions.create(
                    model=model_config['model'],
                    messages=messages,
                    response_format=model_config['response_format'],
                    reasoning_effort=model_config['reasoning_effort'],
                    stream=True
                )
            else:
                stream = client.chat.completions.create(
                    model=model_config['model'],
                    messages=messages,
                    response_format=model_config['response_format'],
                    temperature=model_config['temperature'],
                    max_completion_tokens=model_config['max_completion_tokens'],
                    stream=True
                )
                
            # 將每個收到的token傳送到前端
            for chunk in stream:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield "data: " + json.dumps({"content": content, "done": False}) + "\n\n"
            
            # 發送完成信號，包含完整響應和會話ID
            yield "data: " + json.dumps({
                "content": "", 
                "done": True, 
                "full_response": full_response,
                "session_id": session_id  # 傳回會話ID以便前端用於更新
            }) + "\n\n"
            
        except Exception as e:
            print(f"流式輸出錯誤: {e}")
            error_msg = {"error": str(e)}
            yield "data: " + json.dumps(error_msg) + "\n\n"
    
    return Response(generate(), content_type='text/event-stream')

@app.route("/save_response", methods=["POST"])
@login_required
def save_response():
    """保存API響應到會話中的單獨路由"""
    try:
        data = request.get_json()
        if not data or 'full_response' not in data:
            return jsonify({"success": False, "error": "缺少必要的回應數據"})
        
        full_response = data.get('full_response')
        
        # 更新會話
        messages = session.get('messages', [])
        messages.append({"role": "assistant", "content": full_response})
        session['messages'] = messages
        
        # 更新歷史記錄
        last_user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)
        if last_user_message:
            session['history'].append({"user": last_user_message, "assistant": full_response})
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"保存回應錯誤: {e}")
        return jsonify({"success": False, "error": str(e)})

def initialize_message(user='nobody'):
    if user == 'vinay':
        content = (f"你是一位生活助手，稱呼使用者「尊貴的{NICK}女王」，"
                   "回答應以像男公關對女恩客百般討好的態度回應使用者："
                   "殷勤的、諂媚的、關懷備至的。中文使用正體中文字，勿使用簡體字。")
    elif user == 'takeshi':
        content = ("你是一位生活助手，稱呼使用者「城武哥」，"
                   "回答應以像粉絲對偶像的態度回應使用者:"
                   "崇拜的、敬佩的、支持的。中文使用正體中文字，勿使用簡體字。")
    else:
        content = ("你是一位生活助手，中文使用正體中文字，勿使用簡體字。")
    return [{"role": "system", "content": content}]

def get_openai_response(prompt, messages, model_name='gpt-4o-mini'):
    """非流式回應方式（備用方案）"""
    messages_copy = messages.copy()
    messages_copy.append({"role": "user", "content": prompt})
    try:
        model_config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS['gpt-4o-mini'])
        
        # 根據不同模型使用不同的配置
        if model_name == 'o3-mini':
            completion = client.chat.completions.create(
                model=model_config['model'],
                messages=messages_copy,
                response_format=model_config['response_format'],
                reasoning_effort=model_config['reasoning_effort']
            )
        else:
            completion = client.chat.completions.create(
                model=model_config['model'],
                messages=messages_copy,
                response_format=model_config['response_format'],
                temperature=model_config['temperature'],
                max_completion_tokens=model_config['max_completion_tokens']
            )
        
        assistant_response = completion.choices[0].message.content
        messages_copy.append({"role": "assistant", "content": assistant_response})
        return assistant_response, messages_copy
    except Exception as e:
        print(f"Exception when calling OpenAI API: {e}")
        return "抱歉，發生錯誤。請稍後再試。", messages_copy

if __name__ == '__main__':
    app.run(
        debug=True
    )