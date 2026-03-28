# 慧眼 - 媒体内容真实性检测 API

帮助老年人识别网络虚假信息的分析后端。

## 功能

- 支持微信公众号文章链接分析
- 支持抖音视频内容分析
- 支持纯文本内容分析
- ARG（可接受性-相关性-充分性）逻辑分析框架
- 网络搜索辅助验证（新闻类内容）
- 实时调试输出

## 安装

```bash
cd backend
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件：

```
DEEPSEEK_API_KEY=你的DeepSeek_API密钥
```

## 运行

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API 端点

- `GET /` - API 状态
- `GET /test` - 测试页面
- `POST /analyze` - 分析内容

## 请求示例

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mp.weixin.qq.com/s/xxx"}'
```

## 分析流程

1. 提取系统时间
2. 判断文章类型
3. 网络搜索（新闻类）
4. 建立逻辑链
5. ARG 三重验证
6. 最终判断
