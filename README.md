# 信息鉴别助手 (Media Filter)

帮助老年人识别网络虚假信息的手机应用。

## 项目结构

```
media_filter/
├── backend/          # Python FastAPI 后端
│   ├── main.py       # API 服务
│   ├── requirements.txt
│   └── .env.example
└── mobile/           # Expo React Native 移动端
    ├── app/          # 应用页面
    ├── lib/          # 工具函数
    └── package.json
```

## 快速开始

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填入你的 DEEPSEEK_API_KEY

# 启动服务
python main.py
```

后端将在 http://localhost:8000 运行

### 2. 启动移动端

```bash
cd mobile

# 安装依赖
npm install

# 启动开发服务器
npm start
```

扫描二维码在 Expo Go 应用中预览。

**注意**：如果在真机上测试，需要修改 `lib/api.ts` 中的 `API_BASE_URL` 为你电脑的局域网 IP 地址。

## 功能

- [x] 微信公众号文章链接分析
- [x] 直接文字输入分析
- [x] 可信度判定（可信/需谨慎/不可信）
- [x] 详细分析说明
- [ ] 抖音视频分析（规划中）
- [ ] 视频号分析（规划中）

## 技术栈

- **后端**: Python, FastAPI, BeautifulSoup, DeepSeek API
- **移动端**: React Native, Expo, TypeScript

## Computerization

由 Computerization 社团开发，致力于用技术帮助社区。
