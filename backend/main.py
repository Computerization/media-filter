import os
import re
from typing import Optional

import httpx
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    content: str  # Unified input field - can be URL or text
    # Deprecated fields (kept for backward compatibility)
    url: Optional[str] = None
    text: Optional[str] = None



class AnalyzeResponse(BaseModel):
    title: str
    verdict: str  # "reliable", "caution", "misleading"
    verdict_emoji: str
    summary: str
    details: str
    original_text: str
    score: Optional[int] = None  # Add trust score (0-10)
    input_type: str  # "url" or "text" - shows what was detected



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
# UI
# shilaohua
# 引用名言
# 引用事例
def detect_input_type(input_string: str) -> tuple[str, str]:
    """
    Detect if input is a URL or plain text.
    Returns: (type, normalized_input) where type is 'url' or 'text'
    """
    if not input_string:
        return ("text", "")
    
    # Remove leading/trailing whitespace
    cleaned = input_string.strip()
    
    # URL pattern detection
    url_patterns = [
        r'^https?://',  # Starts with http:// or https://
        r'^www\.',  # Starts with www.
        r'weixin\.qq\.com',  # WeChat domain
        r'mp\.weixin\.qq\.com',  # WeChat MP domain
    ]
    
    for pattern in url_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            # Normalize URL: add https:// if missing
            if not cleaned.startswith(('http://', 'https://')):
                cleaned = 'https://' + cleaned
            return ("url", cleaned)
    
    # Check if it looks like a URL without protocol (contains domain-like structure)
    if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', cleaned):
        cleaned = 'https://' + cleaned
        return ("url", cleaned)
    
    return ("text", cleaned)

def analyze_with_llm(title: str, content: str, author: str) -> dict:
    """Use DeepSeek to analyze if the content is misleading."""

    prompt = f"""你是一位专业的信息鉴别专家，帮助老年人识别网络虚假信息。请仔细分析以下文章的可信度。

【文章信息】
标题：{title}
来源：{author}

【文章内容】
{content}

【分析维度】请从以下8个维度评估（每项0-10分）：

1. **信息源可靠性**：来源是否权威？是否有官方认证？
2. **内容真实性**：事实陈述是否有可验证的来源？是否引用权威机构？
3. **语言特征**：是否使用"震惊"、"必看"、"速转"、"不转不是中国人"等煽动性词汇？
4. **逻辑合理性**：论证是否严谨？是否有明显逻辑漏洞？
5. **健康信息准确性**：涉及健康建议时，是否符合现代医学认知？
6. **商业目的**：是否隐藏推销意图？是否诱导购买或添加联系方式？
7. **科学依据**：引用的"研究"、"专家"是否具体可查？
8. **情感操控**：是否利用恐惧、愤怒、焦虑等负面情绪传播？

【常见虚假信息特征识别】
- ❌ 伪科学养生：如"碱性水治癌"、"绿豆治百病"
- ❌ 夸大恐吓：如"再不看就删了"、"XXX已证实致癌"
- ❌ 编造权威：如"哈佛研究"、"央视报道"（但无具体出处）
- ❌ 情感绑架：如"转发给你爱的人"、"为了家人健康"
- ❌ 阴谋论：如"某某隐瞒真相"、"内部消息"
- ❌ 软文推销：文中反复提及某产品或联系方式

【输出格式】（严格按照此格式）
判定：[可信/需谨慎/不可信]
信任度：[X/10分]
简要说明：[一句话总结问题，20-30字]
详细分析：[分点说明问题，包含具体例证，150-250字]
建议：[给老年人的实用建议，50字以内]

【注意事项】
- 使用简单易懂的语言，避免专业术语
- 直接、明确地指出问题，不模棱两可
- 如果是误导信息，必须清楚说明危害
- 如果可信，也要说明判断依据"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,  # Lower temperature for more consistent analysis
    )

    response_text = response.choices[0].message.content or ""

    # Enhanced parsing with scoring
    verdict = "caution"
    verdict_emoji = "⚠️"
    score = 5

    # Extract score
    score_match = re.search(r"信任度[：:]\s*(\d+)", response_text)
    if score_match:
        score = int(score_match.group(1))
        if score >= 7:
            verdict = "reliable"
            verdict_emoji = "✅"
        elif score <= 4:
            verdict = "misleading"
            verdict_emoji = "❌"
        else:
            verdict = "caution"
            verdict_emoji = "⚠️"
    else:
        # Fallback to keyword detection
        if "可信" in response_text[:80] and "不可信" not in response_text[:80]:
            verdict = "reliable"
            verdict_emoji = "✅"
        elif "不可信" in response_text[:80]:
            verdict = "misleading"
            verdict_emoji = "❌"

    # Extract structured components
    summary = ""
    details = ""
    advice = ""

    summary_match = re.search(r"简要说明[：:]\s*(.+?)(?:\n|$)", response_text)
    if summary_match:
        summary = summary_match.group(1).strip()

    details_match = re.search(r"详细分析[：:]\s*(.+?)(?=建议[：:]|\Z)", response_text, re.DOTALL)
    if details_match:
        details = details_match.group(1).strip()

    advice_match = re.search(r"建议[：:]\s*(.+?)(?:\n|$)", response_text, re.DOTALL)
    if advice_match:
        advice = advice_match.group(1).strip()

    # Combine details and advice
    full_details = details
    if advice:
        full_details += f"\n\n💡 建议：{advice}"

    return {
        "verdict": verdict,
        "verdict_emoji": verdict_emoji,
        "summary": summary or "请查看详细分析",
        "details": full_details or response_text,
        "score": score,
    }

@app.get("/")
async def root():
    return {"message": "Media Filter API - 帮助老年人识别网络虚假信息"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_content(request: AnalyzeRequest):
    """Analyze content with auto-detection of URL or text input."""

    # Handle both new unified 'content' field and legacy 'url'/'text' fields
    input_content = request.content if hasattr(request, 'content') and request.content else None
    
    # Backward compatibility
    if not input_content:
        if request.url:
            input_content = request.url
        elif request.text:
            input_content = request.text
    
    if not input_content:
        raise HTTPException(status_code=400, detail="请提供文章链接或文字内容")
    
    # Validate input length
    if len(input_content) > 50000:
        raise HTTPException(status_code=400, detail="内容过长，请限制在50000字符以内")
    
    if len(input_content.strip()) < 10:
        raise HTTPException(status_code=400, detail="内容过短，请提供至少10个字符")
    
    # Auto-detect input type
    input_type, normalized_input = detect_input_type(input_content)
    
    title = "用户输入内容"
    content = ""
    author = "未知"
    
    if input_type == "url":
        # Check if it's a WeChat article URL
        if "mp.weixin.qq.com" in normalized_input or "weixin.qq.com" in normalized_input:
            try:
                article = await extract_wechat_article(normalized_input)
                title = article["title"]
                content = article["content"]
                author = article["author"]
            except Exception as e:
                # Fallback: if URL extraction fails, treat as text
                raise HTTPException(
                    status_code=400,
                    detail=f"无法提取文章内容：{str(e)}。请尝试复制文章内容直接粘贴分析。"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="目前仅支持微信公众号文章链接。其他链接请复制文章内容后直接粘贴分析。"
            )
    else:
        # Direct text input
        content = normalized_input
        # Sanitize content
        content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
        content = content.strip()
    
    # Validate content is not empty
    if not content or len(content) < 10:
        raise HTTPException(status_code=400, detail="文章内容不能为空或过短")
    
    # Analyze with LLM
    analysis = analyze_with_llm(title, content, author)
    
    return AnalyzeResponse(
        title=title,
        verdict=analysis["verdict"],
        verdict_emoji=analysis["verdict_emoji"],
        summary=analysis["summary"],
        details=analysis["details"],
        original_text=content[:500] + "..." if len(content) > 500 else content,
        score=analysis.get("score"),
        input_type=input_type,
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
