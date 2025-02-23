# Flask ChatGPT 聊天應用

基於 Flask 框架建構的個人化聊天機器人應用，整合 OpenAI API 並支援多角色介面與模型切換。

## 主要功能

- 🔐 登入驗證系統 (main.py:55-61)
- 👑 三種使用者角色介面 (chat_queen.html, chat_takeshi.html, chat_nobody.html)
- 🤖 雙 AI 模型切換 (gpt-4o-mini / o3-mini)
- 📝 Markdown 即時渲染與程式碼複製功能
- ⌨️ Ctrl+Enter 快速傳送
- 💬 對話歷史持久化儲存
- 🎨 自適應深色主題介面

## 技術堆疊

- **後端**: Python/Flask + Flask-Session
- **前端**: Bootstrap 5 + Marked.js
- **AI 整合**: OpenAI API
- **部署**: 原生 WSGI 伺服器

## 安裝步驟

1. 複製儲存庫

```bash
git clone https://github.com/your-repo/flask_with_ChatGPT.git
cd flask_with_ChatGPT
```

2. 安裝依賴套件
```bash
pip install -r requirements.txt
```

3. 環境變數設定 (.env)
```env
FLASK_SECRET_KEY=your_secret_key
VINAY=vinay_password
TAKESHI=takeshi_password
NOBODY=nobody_password
OPENAI_API_KEY=your_openai_key
```

## 使用說明

1. 存取 `/login` 輸入對應密碼進入：
   - 女王模式 (VINAY_PASSWORD)
   - 粉絲模式 (TAKESHI_PASSWORD)
   - 普通模式 (NOBODY_PASSWORD)

2. 功能操作：
   - 下拉選單切換 AI 模型
   - 文字框支援 Markdown 語法
   - 程式碼區塊自動新增複製按鈕
   - Ctrl/Cmd + Enter 快速傳送

3. 介面特點：
   - 自適應捲軸樣式
   - 響應式佈局
   - 載入動畫指示
   - 錯誤即時回饋

## 介面截圖
<!-- 此處可新增截圖 -->

## 程式碼結構
```
flask_with_ChatGPT/
├── main.py                 # 主程式 (路由/工作階段/API 整合)
├── templates/              # 介面範本
│   ├── chat_queen.html     # 女王專屬介面
│   ├── chat_takeshi.html   # 粉絲專屬介面 
│   ├── chat_nobody.html    # 普通使用者介面
│   └── login.html          # 登入頁面
├── static/                 # 靜態資源
├── .env.example            # 環境變數範例
├── requirements.txt        # 依賴列表
└── README.md               # 說明文件
```

## 擴充建議

1. 新增資料庫支援持久化歷史記錄
2. 實作多語言支援
3. 增加更多 AI 模型選項
4. 新增管理員控制面板
5. 實作檔案上傳功能
