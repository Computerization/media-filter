import os
import re
from typing import Optional, List
import asyncio
import json

import httpx
from fastapi.responses import StreamingResponse
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from f2.apps.douyin import DouyinAwemeIdFetcher, DouyinHandler
    DOUYIN_AVAILABLE = True
except ImportError:
    DOUYIN_AVAILABLE = False

load_dotenv()

app = FastAPI(title="Media Filter API", description="Help elderly identify misleading content")

# Allow cross-origin requests from mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DeepSeek client (OpenAI-compatible)
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


class AnalyzeRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None  # Allow direct text input as fallback


class AnalyzeResponse(BaseModel):
    title: str
    verdict: str  # "reliable", "caution", "misleading"
    verdict_emoji: str
    summary: str
    details: str
    original_text: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    title: Optional[str] = None
    original_text: Optional[str] = None
    analysis_summary: Optional[str] = None
    analysis_details: Optional[str] = None


async def extract_wechat_article(url: str) -> dict:
    """Extract content from WeChat Official Account article."""
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as http_client:
        response = await http_client.get(url, headers=headers)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title = ""
    title_elem = soup.find("h1", class_="rich_media_title") or soup.find("h1")
    if title_elem:
        title = title_elem.get_text(strip=True)

    # Extract main content
    content = ""
    content_elem = soup.find("div", class_="rich_media_content") or soup.find("div", id="js_content")
    if content_elem:
        # Get text, preserving some structure
        content = content_elem.get_text(separator="\n", strip=True)

    # Extract author/account name
    author = ""
    author_elem = soup.find("a", class_="weui-wa-hotarea") or soup.find("span", class_="rich_media_meta_nickname")
    if author_elem:
        author = author_elem.get_text(strip=True)

    if not content:
        raise HTTPException(status_code=400, detail="无法提取文章内容，请检查链接是否正确")

    return {
        "title": title or "未知标题",
        "content": content[:8000],  # Limit content length for LLM
        "author": author or "未知来源",
    }


async def extract_douyin_video(url: str) -> dict:
    """Extract content from Douyin video."""
    if not DOUYIN_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="Douyin支持尚未配置，请安装F2库"
        )

    try:
        # Extract video ID from URL
        video_id = DouyinAwemeIdFetcher.get_aweme_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="无法识别抖音视频链接")

        # Fetch video data
        handler = DouyinHandler()
        video_data = await handler.fetch_one_video(video_id)

        # Extract description and comments
        title = video_data.desc or "抖音视频"
        content = video_data.desc or ""
        author = video_data.author.nickname if video_data.author else "未知用户"

        # TODO: Future enhancement - extract audio and transcribe for full content
        if not content:
            raise HTTPException(
                status_code=400,
                detail="无法提取视频内容，请检查链接是否有效"
            )

        return {
            "title": title[:200],  # Limit title
            "content": content[:8000],  # Limit content length for LLM
            "author": author,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法提取抖音视频内容: {str(e)}"
        )


def analyze_with_llm(title: str, content: str, author: str) -> dict:
    """Use DeepSeek to analyze if the content is misleading."""

    prompt = f"""你是一位帮助老年人识别网络虚假信息的助手。请分析以下微信公众号文章，判断其可信度。

文章标题：{title}
来源账号：{author}

文章内容：
{content}

请从以下几个方面分析：
1. 是否包含虚假健康信息或伪科学
2. 是否是广告软文或推销产品
3. 是否使用夸张、恐吓性语言
4. 信息来源是否可靠
5. 是否有明显的逻辑错误

请用简单易懂的语言回复，适合老年人阅读。直接、坚决地给出回复。内容要口语化，生动，适老化。

回复格式：
判定：[可信/需谨慎/不可信]
简要说明：[一句话总结，不超过30字]
详细分析：[具体分析，100-200字]"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )

    response_text = response.choices[0].message.content or ""

    # Parse the response
    verdict = "caution"
    verdict_emoji = "⚠️"

    if "可信" in response_text[:50] and "不可信" not in response_text[:50]:
        verdict = "reliable"
        verdict_emoji = "✅"
    elif "不可信" in response_text[:50]:
        verdict = "misleading"
        verdict_emoji = "❌"
    elif "需谨慎" in response_text[:50] or "谨慎" in response_text[:50]:
        verdict = "caution"
        verdict_emoji = "⚠️"

    # Extract summary and details
    summary = ""
    details = response_text

    summary_match = re.search(r"简要说明[：:]\s*(.+?)(?:\n|详细)", response_text)
    if summary_match:
        summary = summary_match.group(1).strip()

    details_match = re.search(r"详细分析[：:]\s*(.+)", response_text, re.DOTALL)
    if details_match:
        details = details_match.group(1).strip()

    return {
        "verdict": verdict,
        "verdict_emoji": verdict_emoji,
        "summary": summary or "请查看详细分析",
        "details": details,
    }


@app.get("/")
async def root():
    return {"message": "Media Filter API - 帮助老年人识别网络虚假信息"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_content(request: AnalyzeRequest):
    """Analyze content from URL or direct text input."""

    if not request.url and not request.text:
        raise HTTPException(status_code=400, detail="请提供文章链接或文字内容")

    title = "用户输入内容"
    content = ""
    author = "未知"

    if request.url:
        # Check if it's a WeChat article URL
        if "mp.weixin.qq.com" in request.url or "weixin.qq.com" in request.url:
            article = await extract_wechat_article(request.url)
            title = article["title"]
            content = article["content"]
            author = article["author"]
        # Check if it's a Douyin video URL
        elif "douyin.com" in request.url or "dy.com" in request.url:
            video = await extract_douyin_video(request.url)
            title = video["title"]
            content = video["content"]
            author = video["author"]
        else:
            raise HTTPException(
                status_code=400,
                detail="目前仅支持微信公众号文章（mp.weixin.qq.com）和抖音视频（douyin.com）"
            )
    else:
        content = request.text or ""

    # Validate content is not empty
    if not content:
        raise HTTPException(status_code=400, detail="文章内容不能为空")

    # Analyze with LLM
    analysis = analyze_with_llm(title, content, author)

    return AnalyzeResponse(
        title=title,
        verdict=analysis["verdict"],
        verdict_emoji=analysis["verdict_emoji"],
        summary=analysis["summary"],
        details=analysis["details"],
        original_text=content[:500] + "..." if len(content) > 500 else content,
    )


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Stream chat response with reasoning and content.
    Returns Server-Sent Events (SSE).
    """

    system_prompt = f"""
    你是一位帮助老年人识别网络虚假信息的贴心助手"慧眼"。
    你之前已经分析过这篇文章：
    标题：{request.title or '未知'}
    原文摘要：{request.original_text[:500] if request.original_text else '无'}

    之前的分析结果：
    {request.analysis_summary or '无'}
    {request.analysis_details or '无'}

    现在的任务是回答用户关于这篇文章的后续提问。
    请保持语气亲切、耐心，像一位靠谱的晚辈在给长辈解释。
    回答要通俗易懂，不要用复杂的术语。
    如果是谣言，要温和但坚定地提醒长辈不要相信。

    重要提示：
    1. 直接回复用户的内容，不要在开头加"(温和地)"或"(认真地)"之类的语气描述。
    2. 不要重复"你好"或自我介绍，直接针对问题回答。
    """

    llm_messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    async def event_generator():
        try:
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=llm_messages,
                max_tokens=2000,
                stream=True,
            )

            for chunk in response:
                delta = chunk.choices[0].delta

                # Check for reasoning content (DeepSeek R1 specific)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    data = json.dumps({"text": delta.reasoning_content}, ensure_ascii=False)
                    yield f"event: reasoning\ndata: {data}\n\n"

                # Check for standard content
                if delta.content:
                    data = json.dumps({"text": delta.content}, ensure_ascii=False)
                    yield f"event: content\ndata: {data}\n\n"

        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
