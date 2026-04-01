import os
import re
from typing import Optional, List
import asyncio
import json

import httpx
from fastapi.responses import StreamingResponse, HTMLResponse
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
    article_type: str = ""
    search_info: str = ""
    debug_steps: list = []  # 存放所有 AI 原始输出


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    title: Optional[str] = None
    original_text: Optional[str] = None
    analysis_summary: Optional[str] = None
    analysis_details: Optional[str] = None

def search_web(query: str) -> str:
    """联网搜索信息，使用 Jina AI 读取网页"""
    try:
        # 使用 Jina AI Reader 来读取新闻网站
        # 先尝试读取 Bing 搜索结果
        search_urls = [
            f"https://www.bing.com/search?q={query}",
            f"https://news.google.com/search?q={query}",
        ]
        
        for search_url in search_urls:
            try:
                jina_url = f"https://r.jina.ai/{search_url}"
                with httpx.Client(timeout=25.0) as http:
                    resp = http.get(jina_url)
                    if resp.status_code == 200:
                        content = resp.text
                        # 提取标题和内容
                        lines = content.split('\n')
                        results = []
                        for line in lines[:20]:
                            if line.strip() and len(line.strip()) > 10:
                                results.append(line.strip())
                        if results:
                            return "\n".join(results[:10])
            except Exception:
                continue
        
        return "未能获取搜索结果"
            
    except Exception as e:
        return f"搜索失败: {str(e)}"

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


def parse_logic_chain_to_tree(logic_chain_text: str) -> dict:
    """将逻辑链文本解析为树形结构"""
    tree = {
        "nodes": {},  # 节点ID -> 节点内容
        "edges": [],   # 边: [from_id, to_id, type]
        "original_text": logic_chain_text
    }
    
    lines = logic_chain_text.strip().split('\n')
    node_counter = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 提取依据
        evidence_match = re.search(r'依据(\d+)[：:]\s*(.+)', line)
        if evidence_match:
            node_id = f"E{evidence_match.group(1)}"
            node_content = evidence_match.group(2).strip()
            tree["nodes"][node_id] = {"type": "evidence", "content": node_content}
            continue
        
        # 提取结论（箭头后面的内容）
        conclusion_match = re.search(r'→\s*(.+)', line)
        if conclusion_match:
            node_id = f"C{node_counter}"
            node_content = conclusion_match.group(1).strip()
            tree["nodes"][node_id] = {"type": "conclusion", "content": node_content}
            node_counter += 1
            
            # 解析箭头左边的依据
            arrow_left = line.split('→')[0].strip()
            if '+' in arrow_left:
                # A + B → C
                sources = arrow_left.split('+')
                for src in sources:
                    src = src.strip()
                    tree["edges"].append([src, node_id, "support"])
            else:
                # A → B
                tree["edges"].append([arrow_left.strip(), node_id, "support"])
    
    return tree


def arg_single_check(evidence: str, conclusion: str, arg_type: str, debug_steps: list, current_date: str, current_time: str) -> dict:
    """
    单独的 ARG 检查调用，每次 AI 调用只接收单一输入
    arg_type: "acceptability" | "relevance" | "sufficiency"
    """
    
    type_labels = {
        "acceptability": "验证依据",
        "relevance": "验证观点",
        "sufficiency": "验证结论"
    }
    label = type_labels.get(arg_type, arg_type)
    
    prompts = {
        "acceptability": f"""你是一个逻辑分析专家，只分析我提供的文本，不看任何其他内容。

【系统时间】{current_date} {current_time}
【分析任务】可接受性分析（判断依据本身是否可信）

请分析以下依据的可接受性：
---
{evidence}
---

只回答以下格式（一行）：
依据可接受性：[有效/无效] 理由：[不超过20字]""",
        
        "relevance": f"""你是一个逻辑分析专家，只分析我提供的文本，不看任何其他内容。

【系统时间】{current_date} {current_time}
【分析任务】相关性分析（判断依据是否能支持结论）

请分析以下依据与结论的相关性：
---
依据：{evidence}
结论：{conclusion}
---

只回答以下格式（一行）：
观点支持性：[有效/无效] 理由：[不超过20字]""",
        
        "sufficiency": f"""你是一个逻辑分析专家，只分析我提供的文本，不看任何其他内容。

【系统时间】{current_date} {current_time}
【分析任务】充分性分析（判断依据是否足以支持结论）

请分析以下依据对结论的充分性：
---
依据：{evidence}
结论：{conclusion}
---

只回答以下格式（一行）：
结论充分性：[有效/无效] 理由：[不超过20字]"""
    }
    
    prompt = prompts.get(arg_type, prompts["acceptability"])
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
    )
    
    result_text = response.choices[0].message.content or ""
    
    valid = "有效" in result_text
    
    debug_steps.append({
        "step": f"[{'✓' if valid else '✗'}] {label}",
        "prompt": f"依据：{evidence[:100]}...\n结论：{conclusion[:100] if conclusion else 'N/A'}...",
        "response": result_text
    })
    
    return {
        "arg_type": arg_type,
        "evidence": evidence,
        "conclusion": conclusion,
        "response": result_text,
        "passed": valid,
        "valid": valid
    }


def build_logic_chain_prompt(title: str, content: str, search_info: str, current_date: str, current_time: str, iteration: int = 0) -> str:
    """生成建立逻辑链的 prompt"""
    retry_note = ""
    if iteration > 0:
        retry_note = f"\n【注意】这是第{iteration+1}次尝试，请确保逻辑链满足ARG标准。"
    
    return f"""你是一个逻辑分析专家。请分析以下文章的论证结构，建立完整的逻辑链。

【系统时间】{current_date} {current_time}{retry_note}

文章标题：{title}
{search_info}
文章内容：
{content}

请按以下格式建立逻辑链（由依据指向结论）：
1. 先列出所有【原始依据/事实】（文章中明确提到的事件、数据、声明等）
2. 然后用箭头表示推理关系

格式（必须严格遵守）：
依据1：[具体事实/事件/数据]
依据2：[具体事实/事件/数据]
...
依据N：[具体事实/事件/数据]
依据1 + 依据2 → 中间结论1
中间结论1 + 依据3 → 中间结论2
...
中间结论X → 最终结论

重要：
- 逻辑链必须完整，每个结论都要有依据支撑
- 箭头表示"由...推出..."
- 原始依据必须是文章中明确提到的内容
- 中间结论是从原始依据推导出来的
- 最终结论是文章的最终主张"""


def analyze_with_llm(title: str, content: str, author: str) -> dict:
    import datetime
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.strftime("%Y年%m月%d日")
    current_time = current_datetime.strftime("%H:%M:%S")
    
    debug_steps = []
    
    # 第0步：获取当前日期时间
    debug_steps.append({
        "step": "0. 当前系统时间",
        "prompt": "",
        "response": f"当前日期：{current_date}，当前时间：{current_time}"
    })
    
    # 第一步：判断文章类型
    type_check_prompt = f"""请判断以下文章属于哪种类型，只需要回答类型名称。

文章标题：{title}
来源账号：{author}
文章内容（前500字）：{content[:500]}

可选类型（只选一个）：
- 新闻资讯
- 健康养生
- 金融投资
- 情感心理
- 生活常识
- 娱乐八卦
- 广告软文
- 其他

请直接回答类型名称，不要多余文字。"""

    type_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": type_check_prompt}],
        max_tokens=50,
    )
    article_type = type_response.choices[0].message.content or ""
    
    debug_steps.append({
        "step": "1. 判断文章类型",
        "prompt": type_check_prompt,
        "response": article_type
    })
    
    # 第二步：网络搜索（如果是新闻类）
    need_search = any(keyword in article_type for keyword in ["新闻", "时事", "政治", "国际", "经济"])
    search_info = ""
    
    if need_search:
        keywords = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,15}', title)
        stop_words = ["已经", "美国", "中国", "俄罗斯", "最新", "消息", "新闻", "报道", "关于", "对于"]
        keywords = [k for k in keywords if k not in stop_words and len(k) > 2]
        search_query = " ".join(keywords[:8])
        
        if search_query:
            search_result = search_web(f"{current_date} {current_time} {search_query}")
            if search_result and "失败" not in search_result:
                search_info = f"\n\n【网络搜索结果】\n{search_result[:1500]}\n【搜索结束】\n"
                debug_steps.append({
                    "step": "2. 网络搜索",
                    "prompt": f"【系统时间】{current_date} {current_time}，搜索关键词: {search_query}",
                    "response": search_result[:500]
                })
    
    # 第三步：建立逻辑链（可能需要多次迭代）
    max_logic_iterations = 3
    final_logic_chain = ""
    logic_chain = ""
    arg_results = []
    logic_passed = False
    
    for iteration in range(max_logic_iterations):
        logic_prompt = build_logic_chain_prompt(
            title, content, search_info, current_date, current_time, iteration
        )
        
        logic_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": logic_prompt}],
            max_tokens=1500,
        )
        
        logic_chain = logic_response.choices[0].message.content or ""
        
        debug_steps.append({
            "step": f"3.{iteration+1}. 建立逻辑链 (第{iteration+1}次)",
            "prompt": logic_prompt,
            "response": logic_chain
        })
        
        # 解析逻辑链为树形结构
        tree = parse_logic_chain_to_tree(logic_chain)
        
        # 添加逻辑链树形图到调试输出
        tree_viz = "【逻辑链结构】\n"
        for node_id, node in tree["nodes"].items():
            tree_viz += f"{node_id} [{node['type']}]: {node['content'][:80]}...\n"
        for edge in tree["edges"]:
            tree_viz += f"  {edge[0]} → {edge[1]} ({edge[2]})\n"
        
        debug_steps.append({
            "step": f"3.{iteration+1}. 逻辑链结构",
            "prompt": "",
            "response": tree_viz
        })
        
        if not tree["nodes"]:
            debug_steps.append({
                "step": f"3.{iteration+1}. 解析失败",
                "prompt": "",
                "response": "无法解析逻辑链，重试中..."
            })
            continue
        
        # ARG 分析 - 每次单独调用 AI，每次只看当前内容
        current_arg_results = []
        all_checks_passed = True
        
        # 1. 先收集所有需要检查的项
        check_items = []
        
        # 对每个节点检查可接受性
        for node_id, node in tree["nodes"].items():
            check_items.append({
                "type": "acceptability",
                "evidence": node["content"],
                "conclusion": "",
                "description": f"{node_id} ({node['type']}) 的可接受性"
            })
        
        # 对每条边检查相关性
        for edge in tree["edges"]:
            source_id, target_id, edge_type = edge
            if source_id in tree["nodes"] and target_id in tree["nodes"]:
                source_content = tree["nodes"][source_id]["content"]
                target_content = tree["nodes"][target_id]["content"]
                
                check_items.append({
                    "type": "relevance",
                    "evidence": source_content,
                    "conclusion": target_content,
                    "description": f"{source_id} → {target_id} 的相关性"
                })
        
        # 对每个结论检查充分性（所有指向它的依据一起支持）
        conclusion_sources = {}
        for edge in tree["edges"]:
            source_id, target_id, edge_type = edge
            if target_id not in conclusion_sources:
                conclusion_sources[target_id] = []
            if source_id in tree["nodes"]:
                conclusion_sources[target_id].append(tree["nodes"][source_id]["content"])
        
        for target_id, sources in conclusion_sources.items():
            if len(sources) >= 1 and target_id in tree["nodes"]:
                combined_evidence = " + ".join(sources)
                target_content = tree["nodes"][target_id]["content"]
                
                check_items.append({
                    "type": "sufficiency",
                    "evidence": combined_evidence,
                    "conclusion": target_content,
                    "description": f"{' + '.join(list(conclusion_sources.keys())[:3])} → {target_id} 的充分性"
                })
        
        # 执行所有检查
        debug_steps.append({
            "step": f"3.{iteration+1}. 开始ARG分析 (共{len(check_items)}项)",
            "prompt": "",
            "response": f"检查项：{', '.join([c['type'] for c in check_items])}"
        })
        
        for i, check in enumerate(check_items):
            result = arg_single_check(
                evidence=check["evidence"],
                conclusion=check["conclusion"],
                arg_type=check["type"],
                debug_steps=debug_steps,
                current_date=current_date,
                current_time=current_time
            )
            current_arg_results.append({
                "check": check,
                "result": result
            })
            
            if not result["passed"]:
                all_checks_passed = False
        
        # 如果所有检查都通过，逻辑链有效
        if all_checks_passed:
            logic_passed = True
            final_logic_chain = logic_chain
            arg_results = current_arg_results
            break
        else:
            # 找出失败的检查
            failed = [r for r in current_arg_results if not r["result"]["passed"]]
            failed_info = "\n".join([
                f"- {r['check']['type']}: {r['check']['description']} → {r['result']['response']}"
                for r in failed[:3]
            ])
            
            debug_steps.append({
                "step": f"3.{iteration+1}. ARG检查未通过",
                "prompt": "",
                "response": f"失败项：\n{failed_info}\n\n正在重新建立逻辑链..."
            })
    
    # 如果最终没有通过，返回最后一次的逻辑链
    if not logic_passed and arg_results:
        final_logic_chain = logic_chain
    
    # 第四步：结合 ARG 结果和搜索信息，给出最终判断
    arg_summary = "\n".join([
        f"[{r['check']['type'][:3].upper()}] {r['check']['description']}: {r['result']['response'][:50]} {'✓' if r['result']['passed'] else '✗'}"
        for r in arg_results
    ])
    
    # 统计通过率
    total_checks = len(arg_results)
    passed_checks = sum(1 for r in arg_results if r["result"]["passed"])
    pass_rate = f"{passed_checks}/{total_checks}" if total_checks > 0 else "N/A"
    
    debug_steps.append({
        "step": "4. ARG分析汇总",
        "prompt": "",
        "response": f"通过率：{pass_rate}\n{arg_summary[:500]}"
    })
    
    final_prompt = f"""你是一位帮助老年人识别网络虚假信息的助手。请根据以下所有信息综合判断文章可信度。

【重要】当前系统时间：{current_date} {current_time}

文章标题：{title}
来源账号：{author}
文章类型：{article_type}
{search_info}
文章内容：
{content}

【ARG逻辑分析结果】
{arg_summary}

【ARG分析通过率】：{pass_rate}

【重要判断原则】（必须遵守）
1. 不要因为权威媒体没有报道就判定为假：很多真实信息可能不在新华社、央视等主流媒体发布
2. 重点核实：逻辑是否自洽、论据是否可靠、是否有多个独立信源佐证
3. 如果ARG分析通过率高（>70%），说明文章论证逻辑较严谨
4. 如果ARG分析通过率低，说明文章论证存在明显问题
5. 严禁自己获取或推断当前时间

请综合以上所有信息判断可信度。

回复格式：
判定：[可信/需谨慎/不可信]
简要说明：[一句话总结，不超过30字]
详细分析：[具体分析，150-300字]"""

    final_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": final_prompt}],
        max_tokens=1024,
    )

    response_text = final_response.choices[0].message.content or ""
    
    debug_steps.append({
        "step": "5. 最终判断",
        "prompt": final_prompt,
        "response": response_text
    })
    
    return {
        "debug_steps": debug_steps,
        "final_response": response_text,
        "arg_pass_rate": pass_rate,
        "arg_summary": arg_summary
    }


@app.get("/")
async def root():
    return {"message": "Media Filter API - 帮助老年人识别网络虚假信息"}


@app.get("/test")
async def test_page():
    return HTMLResponse("""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>慧眼 - 信息真假识别</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #8B4513;
            --primary-light: #A0522D;
            --gold: #D4AF37;
            --gold-light: #F4E4BA;
            --cream: #FDF5E6;
            --ink: #2C2C2C;
            --ink-light: #5A5A5A;
            --red-badge: #C41E3A;
            --green-badge: #2E7D32;
            --orange-badge: #E65100;
            --shadow: rgba(139, 69, 19, 0.15);
            --shadow-heavy: rgba(139, 69, 19, 0.25);
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: var(--cream);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(212, 175, 55, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(139, 69, 19, 0.06) 0%, transparent 50%),
                url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
            pointer-events: none;
            z-index: 0;
        }
        
        .bg-decoration {
            position: fixed;
            width: 400px;
            height: 400px;
            border: 1px solid rgba(212, 175, 55, 0.1);
            border-radius: 50%;
            pointer-events: none;
            z-index: 0;
        }
        
        .bg-decoration.top-right {
            top: -100px;
            right: -100px;
            width: 300px;
            height: 300px;
        }
        
        .bg-decoration.bottom-left {
            bottom: -150px;
            left: -150px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 24px 60px;
            position: relative;
            z-index: 1;
            display: flex;
            gap: 24px;
        }
        
        .main-content {
            flex: 1;
            min-width: 0;
        }
        
        .debug-panel {
            width: 480px;
            flex-shrink: 0;
            background: #0d0d0d;
            border-radius: 12px;
            padding: 16px;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            line-height: 1.5;
            max-height: 80vh;
            overflow-y: auto;
            position: sticky;
            top: 20px;
            transition: all 0.3s ease;
            border: 1px solid #333;
        }
        
        .debug-panel.fullscreen {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100vw;
            max-height: 100vh;
            border-radius: 0;
            z-index: 9999;
            padding: 20px;
        }
        
        .debug-panel-toggle {
            background: #333;
            color: #fff;
            border: none;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            margin-left: 8px;
        }
        
        .debug-panel-toggle:hover {
            background: #555;
        }
        
        .debug-panel h3 {
            color: #fff;
            margin: 0 0 12px 0;
            font-size: 13px;
            font-weight: normal;
            display: flex;
            align-items: center;
        }
        
        .debug-output {
            color: #ccc;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .debug-output .line {
            margin-bottom: 8px;
        }
        
        .debug-output .title {
            color: #fff;
            font-weight: bold;
            margin-bottom: 2px;
        }
        
        .debug-output .input {
            color: #888;
            margin-left: 8px;
            border-left: 2px solid #444;
            padding-left: 8px;
            margin-bottom: 4px;
        }
        
        .debug-output .output {
            color: #00ff00;
            margin-left: 8px;
        }
        
        .debug-output .valid {
            color: #00ff00;
        }
        
        .debug-output .invalid {
            color: #ff6666;
        }
        
        .debug-output .separator {
            color: #555;
            margin: 8px 0;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
            animation: fadeInDown 0.8s ease-out;
        }
        
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .logo {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        
        .logo-icon {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 0 8px 24px var(--shadow-heavy);
        }
        
        .logo-text {
            font-family: 'Noto Serif SC', serif;
            font-size: 36px;
            font-weight: 700;
            color: var(--ink);
            letter-spacing: 4px;
        }
        
        .tagline {
            font-size: 16px;
            color: var(--ink-light);
            letter-spacing: 2px;
        }
        
        .card {
            background: white;
            border-radius: 24px;
            padding: 32px;
            box-shadow: 
                0 4px 24px var(--shadow),
                0 1px 2px rgba(0,0,0,0.04);
            border: 1px solid rgba(212, 175, 55, 0.15);
            position: relative;
            overflow: hidden;
            animation: fadeInUp 0.6s ease-out 0.2s both;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--gold), var(--primary), var(--gold));
        }
        
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .input-section {
            margin-bottom: 24px;
        }
        
        .input-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 18px;
            font-weight: 500;
            color: var(--ink);
            margin-bottom: 16px;
        }
        
        .input-label-icon {
            width: 28px;
            height: 28px;
            background: var(--gold-light);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .textarea-wrapper {
            position: relative;
        }
        
        textarea {
            width: 100%;
            min-height: 180px;
            padding: 20px;
            border: 2px solid #E8E0D5;
            border-radius: 16px;
            font-size: 17px;
            line-height: 1.7;
            font-family: inherit;
            resize: vertical;
            transition: all 0.3s ease;
            background: #FDFCFA;
            color: var(--ink);
        }
        
        textarea::placeholder {
            color: #A99585;
        }
        
        textarea:focus {
            outline: none;
            border-color: var(--gold);
            box-shadow: 0 0 0 4px rgba(212, 175, 55, 0.15);
            background: white;
        }
        
        .analyze-btn {
            width: 100%;
            padding: 18px 32px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            border: none;
            border-radius: 16px;
            font-size: 20px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: all 0.3s ease;
            box-shadow: 0 8px 24px var(--shadow-heavy);
            letter-spacing: 2px;
        }
        
        .analyze-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 12px 32px var(--shadow-heavy);
        }
        
        .analyze-btn:active:not(:disabled) {
            transform: translateY(0);
        }
        
        .analyze-btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        
        .analyze-btn-icon {
            font-size: 22px;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 48px 24px;
            background: rgba(244, 228, 186, 0.3);
            border-radius: 16px;
            margin: 24px 0;
        }
        
        .loading.show {
            display: block;
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .loading-text {
            font-size: 18px;
            color: var(--primary);
            margin-top: 16px;
        }
        
        .loading-dots::after {
            content: '';
            animation: dots 1.5s steps(4, end) infinite;
        }
        
        @keyframes dots {
            0% { content: ''; }
            25% { content: '.'; }
            50% { content: '..'; }
            75% { content: '...'; }
        }
        
        .result {
            display: none;
            margin-top: 32px;
            animation: slideIn 0.5s ease-out;
        }
        
        .result.show {
            display: block;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-header {
            text-align: center;
            padding: 28px;
            border-radius: 20px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }
        
        .result-header::after {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 50%);
            pointer-events: none;
        }
        
        .result-header.reliable {
            background: linear-gradient(135deg, #1B5E20 0%, #388E3C 100%);
        }
        
        .result-header.caution {
            background: linear-gradient(135deg, #E65100 0%, #F57C00 100%);
        }
        
        .result-header.misleading {
            background: linear-gradient(135deg, #B71C1C 0%, #C62828 100%);
        }
        
        .verdict-emoji {
            font-size: 56px;
            margin-bottom: 8px;
            display: block;
            animation: bounceIn 0.6s ease-out;
        }
        
        @keyframes bounceIn {
            0% { transform: scale(0.5); opacity: 0; }
            60% { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
        
        .verdict-text {
            color: white;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 4px;
        }
        
        .result-card {
            background: #FAF8F5;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            border: 1px solid rgba(139, 69, 19, 0.1);
        }
        
        .result-card-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 15px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .result-card-content {
            font-size: 17px;
            line-height: 1.8;
            color: var(--ink);
        }
        
        .result-card-content.summary {
            font-size: 19px;
            font-weight: 500;
            color: var(--ink);
            padding: 16px;
            background: white;
            border-radius: 12px;
            border-left: 4px solid var(--gold);
        }
        
        footer {
            text-align: center;
            margin-top: 40px;
            padding: 24px;
            color: var(--ink-light);
            font-size: 14px;
            opacity: 0.7;
        }
        
        footer a {
            color: var(--primary);
            text-decoration: none;
        }
        
        @media (max-width: 640px) {
            .container { padding: 24px 16px 40px; }
            .logo-text { font-size: 28px; }
            .card { padding: 24px 20px; }
            textarea { min-height: 150px; font-size: 16px; }
            .analyze-btn { font-size: 18px; padding: 16px 24px; }
            .verdict-text { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="bg-decoration top-right"></div>
    <div class="bg-decoration bottom-left"></div>
    
    <div class="container">
        <div class="main-content">
        <header>
            <div class="logo">
                <div class="logo-icon">👁</div>
                <span class="logo-text">慧眼</span>
            </div>
            <p class="tagline">帮助长辈辨别网络虚假信息</p>
        </header>
        
        <main class="card">
            <div class="input-section">
                <label class="input-label">
                    <span class="input-label-icon">✎</span>
                    请输入要鉴别的内容
                </label>
                <div class="textarea-wrapper">
                    <textarea id="content" placeholder="粘贴微信文章链接或输入需要鉴别的文字...
例如：科学家发现，吃香蕉可以治愈癌症！"></textarea>
                </div>
            </div>
            
            <button id="analyzeBtn" class="analyze-btn" onclick="analyze()">
                <span class="analyze-btn-icon">🔍</span>
                开始分析
            </button>
            
            <div id="loading" class="loading">
                <div style="font-size: 40px; margin-bottom: 8px;">⏳</div>
                <div class="loading-text">正在分析中<span class="loading-dots"></span></div>
            </div>
            
            <div id="result" class="result">
                <div id="verdict" class="result-header">
                    <span id="verdictEmoji" class="verdict-emoji"></span>
                    <div id="verdictText" class="verdict-text"></div>
                </div>
                
                <div class="result-card">
                    <div class="result-card-label">
                        <span>📋</span> 简要说明
                    </div>
                    <div id="summary" class="result-card-content summary"></div>
                </div>
                
                <div class="result-card">
                    <div class="result-card-label">
                        <span>📖</span> 详细分析
                    </div>
                    <div id="details" class="result-card-content"></div>
                </div>
                
                <div class="result-card" id="analysisProcess" style="display:none;">
                    <div class="result-card-label">
                        <span>🔍</span> 分析过程
                    </div>
                    <div id="articleType" class="result-card-content" style="margin-bottom:12px;padding:12px;background:#f0f7ff;border-radius:8px;border-left:3px solid #2196F3;">
                        <strong>文章类型：</strong><span></span>
                    </div>
                    <div id="searchInfo" class="result-card-content" style="display:none;margin-bottom:12px;padding:12px;background:#fff8e1;border-radius:8px;border-left:3px solid #FF9800;">
                        <strong>网络搜索结果：</strong>
                        <pre style="white-space:pre-wrap;word-wrap:break-word;margin-top:8px;font-size:14px;max-height:300px;overflow-y:auto;"></pre>
                    </div>
                </div>
            </div>
        </main>
        
        <footer>
            <p>慧眼 · 守护长辈的数字生活</p>
        </footer>
        </div>
        
        <!-- 右侧调试面板 -->
        <div class="debug-panel" id="debugPanel">
            <h3>AI 调试输出 <button class="debug-panel-toggle" onclick="toggleDebugFullscreen()">全屏</button></h3>
            <div class="debug-output" id="debugContent">等待分析...</div>
        </div>
    </div>
    
    <script>
        function toggleDebugFullscreen() {
            const panel = document.getElementById('debugPanel');
            panel.classList.toggle('fullscreen');
            const btn = panel.querySelector('.debug-panel-toggle');
            btn.textContent = panel.classList.contains('fullscreen') ? '退出全屏' : '全屏';
        }
        
        async function analyze() {
            const content = document.getElementById('content').value.trim();
            if (!content) {
                alert('请输入要鉴别的内容');
                return;
            }
            
            const isUrl = content.startsWith('http://') || content.startsWith('https://');
            const payload = isUrl ? { url: content } : { text: content };
            
            const btn = document.getElementById('analyzeBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            btn.disabled = true;
            btn.innerHTML = '<span class="analyze-btn-icon">⏳</span> 分析中...';
            loading.classList.add('show');
            result.classList.remove('show');
            
            document.getElementById('debugContent').textContent = '开始分析...\n';
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) throw new Error('分析失败');
                
                const data = await response.json();
                
                const verdictEl = document.getElementById('verdict');
                verdictEl.className = 'result-header ' + data.verdict;
                document.getElementById('verdictEmoji').textContent = data.verdict_emoji;
                
                const verdictTexts = {
                    'reliable': '信息可信',
                    'caution': '需要谨慎',
                    'misleading': '不可信'
                };
                document.getElementById('verdictText').textContent = verdictTexts[data.verdict] || data.verdict;
                document.getElementById('summary').textContent = data.summary;
                document.getElementById('details').textContent = data.details;
                
                const analysisProcess = document.getElementById('analysisProcess');
                if (data.article_type || data.search_info) {
                    analysisProcess.style.display = 'block';
                    
                    const articleTypeEl = document.getElementById('articleType');
                    if (data.article_type) {
                        articleTypeEl.querySelector('span').textContent = data.article_type;
                        articleTypeEl.style.display = 'block';
                    } else {
                        articleTypeEl.style.display = 'none';
                    }
                    
                    const searchInfoEl = document.getElementById('searchInfo');
                    if (data.search_info && data.search_info.trim()) {
                        searchInfoEl.querySelector('pre').textContent = data.search_info;
                        searchInfoEl.style.display = 'block';
                    } else {
                        searchInfoEl.style.display = 'none';
                    }
                } else {
                    analysisProcess.style.display = 'none';
                }
                
                // 显示调试面板 - 纯文字输出
                const debugContent = document.getElementById('debugContent');
                if (data.debug_steps && data.debug_steps.length > 0) {
                    let output = '';
                    data.debug_steps.forEach(function(step) {
                        output += '----------------------------------------\n';
                        output += step.step + '\n';
                        if (step.prompt) {
                            output += '[输入]\n' + step.prompt + '\n';
                        }
                        output += '[输出]\n' + (step.response || '') + '\n';
                    });
                    output += '========================================\n';
                    output += '分析完成\n';
                    debugContent.textContent = output;
                } else {
                    debugContent.textContent = '无调试信息';
                }
                
                result.classList.add('show');
                result.scrollIntoView({behavior: 'smooth', block: 'start'});
                
            } catch (err) {
                alert('分析失败: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span class="analyze-btn-icon">🔍</span> 开始分析';
                loading.classList.remove('show');
            }
        }
    </script>
</body>
</html>""")


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
        article_type=analysis.get("article_type", ""),
        search_info=analysis.get("search_info", ""),
        debug_steps=analysis.get("debug_steps", []),
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

    llm_messages: list = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    async def event_generator():
        try:
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=llm_messages,  # type: ignore
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
