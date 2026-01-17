from DrissionPage import ChromiumOptions


path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
ChromiumOptions().set_browser_path(path).save()


from DrissionPage import ChromiumOptions

# --- 浏览器基础配置 ---
CHROME_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
# 初始化配置（如果需要在导入时就生效，保留此行；通常建议在 main.py 或使用处调用）
ChromiumOptions().set_browser_path(CHROME_PATH).save()

# --- 模型抓取配置 ---
# 集中管理 URL 和 CSS 选择器
# 格式说明：
# domain: 用于查找已有标签页的域名片段
# home_url: 如果没找到标签页，新开页面的地址
# selectors: 页面元素选择器，支持字符串或列表（列表用于存放备用选择器）
MODEL_CONFIG = {
    'deepseek': {
        'domain': 'chat.deepseek.com',
        'home_url': 'https://chat.deepseek.com/',
        'selectors': {
            'input': ['css:textarea._27c9245', 'css:textarea[placeholder*="DeepSeek"]'],
            'send': 'css:._7436101',
            'stop': 'css:._7436101',
            'answer': 'css:.ds-markdown'
        }
    },
    'gpt': {
        'domain': 'chatgpt.com',
        'alt_domain': 'openai.com', # GPT 特有的备用域名检测
        'home_url': 'https://www.chatgpt.com/',
        'selectors': {
            'input': ['css:#prompt-textarea p', 'css:#prompt-textarea'],
            'send': ['css:#composer-submit-button', 'css:[data-testid="send-button"]'],
            'stop': 'css:[data-testid="stop-button"]',
            'answer': 'css:.markdown.markdown-new-styling'
        }
    },
    'doubao': {
        'domain': 'dola.com',
        'home_url': 'https://www.dola.com/',
        'selectors': {
            'input': 'css:.semi-input-textarea',
            'send': 'css:#flow-end-msg-send',
            'stop': 'css:#flow-end-msg-send',
            'answer': 'css:.container-P2rR72'
        }
    },
    'gemini': {
        'domain': 'gemini.google.com',
        'home_url': 'https://www.gemini.google.com/',
        'selectors': {
            'input': ['css:.ql-editor.textarea p', 'css:.ql-editor.textarea'],
            'send': 'css:.send-button',
            'stop': 'css:.send-button.stop',
            'answer': 'css:.markdown.markdown-main-panel'
        }
    },
    'kimi': {
        'domain': 'kimi.com',
        'home_url': 'https://www.kimi.com/',
        'selectors': {
            'input': 'css:.chat-input-editor',
            'send': 'css:.send-button-container',
            'stop': 'css:.send-button-container.stop',
            'answer': 'css:.markdown'
        }
    }
}