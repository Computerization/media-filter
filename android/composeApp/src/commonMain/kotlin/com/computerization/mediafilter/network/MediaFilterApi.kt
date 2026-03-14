package com.computerization.mediafilter.network

import com.computerization.mediafilter.data.AnalyzeResponse
import com.computerization.mediafilter.data.ChatRequest
import io.ktor.client.HttpClient
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.preparePost
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsChannel
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import io.ktor.serialization.kotlinx.json.json
import io.ktor.utils.io.readUTF8Line
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

// DeepSeek API Models
@Serializable
data class DeepSeekMessage(
    val role: String,
    val content: String
)

@Serializable
data class DeepSeekRequest(
    val model: String,
    val messages: List<DeepSeekMessage>,
    @SerialName("max_tokens") val maxTokens: Int = 2000,
    val stream: Boolean = false
)

@Serializable
data class DeepSeekChoice(
    val message: DeepSeekMessage? = null,
    val delta: DeepSeekDelta? = null
)

@Serializable
data class DeepSeekDelta(
    val content: String? = null,
    @SerialName("reasoning_content") val reasoningContent: String? = null
)

@Serializable
data class DeepSeekResponse(
    val choices: List<DeepSeekChoice>
)

class MediaFilterApi {
    // ⚠️ API Key embedded in app - can be extracted! Use with caution.
    private val apiKey = "sk-56a2c73e18d04371a7d4c872bfc48931"
    private val deepSeekUrl = "https://api.deepseek.com/chat/completions"

    private val client = HttpClient {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                prettyPrint = true
            })
        }
        install(HttpTimeout) {
            requestTimeoutMillis = 180_000  // 3 minutes for LLM response
            connectTimeoutMillis = 30_000
            socketTimeoutMillis = 180_000
        }
    }

    private val jsonParser = Json { ignoreUnknownKeys = true }

    /**
     * Extract article content from WeChat URL
     */
    private suspend fun extractWeChatArticle(url: String): Triple<String, String, String> {
        val response = client.get(url) {
            header("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15")
        }

        if (!response.status.isSuccess()) {
            throw Exception("无法访问文章链接")
        }

        val html = response.bodyAsText()

        // Extract title
        val titleRegex = """<h1[^>]*class="[^"]*rich_media_title[^"]*"[^>]*>([\s\S]*?)</h1>""".toRegex()
        val titleMatch = titleRegex.find(html)
        val title = titleMatch?.groupValues?.get(1)?.trim()
            ?.replace(Regex("<[^>]+>"), "")
            ?.replace("&nbsp;", " ")
            ?.trim()
            ?: run {
                // Fallback: try og:title
                val ogTitleRegex = """<meta[^>]*property="og:title"[^>]*content="([^"]*)"[^>]*>""".toRegex()
                ogTitleRegex.find(html)?.groupValues?.get(1) ?: "未知标题"
            }

        // Extract content
        val contentRegex = """<div[^>]*class="[^"]*rich_media_content[^"]*"[^>]*id="js_content"[^>]*>([\s\S]*?)</div>\s*<script""".toRegex()
        val contentMatch = contentRegex.find(html)
        var content = contentMatch?.groupValues?.get(1)
            ?: run {
                // Fallback: simpler pattern
                val fallbackRegex = """id="js_content"[^>]*>([\s\S]*?)</div>""".toRegex()
                fallbackRegex.find(html)?.groupValues?.get(1) ?: ""
            }

        // Clean HTML tags and decode entities
        content = content
            .replace(Regex("<br\\s*/?>"), "\n")
            .replace(Regex("<p[^>]*>"), "\n")
            .replace(Regex("</p>"), "\n")
            .replace(Regex("<[^>]+>"), "")
            .replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
            .replace("&quot;", "\"")
            .replace(Regex("\\s+"), " ")
            .trim()

        if (content.isEmpty()) {
            throw Exception("无法提取文章内容，请检查链接是否正确")
        }

        // Extract author
        val authorRegex = """<a[^>]*class="[^"]*weui-wa-hotarea[^"]*"[^>]*>([\s\S]*?)</a>""".toRegex()
        val author = authorRegex.find(html)?.groupValues?.get(1)
            ?.replace(Regex("<[^>]+>"), "")
            ?.trim()
            ?: "未知来源"

        return Triple(title, content.take(8000), author)
    }

    /**
     * Analyze content using DeepSeek LLM
     */
    private suspend fun analyzeWithLLM(title: String, content: String, author: String): AnalyzeResponse {
        val prompt = """你是一位帮助老年人识别网络虚假信息的助手。请分析以下微信公众号文章，判断其可信度。

文章标题：$title
来源账号：$author

文章内容：
${content.take(6000)}

请从以下几个方面分析：
1. 是否包含虚假健康信息或伪科学
2. 是否是广告软文或推销产品
3. 是否使用夸张、恐吓性语言
4. 信息来源是否可靠
5. 是否有明显的逻辑错误

请用简单易懂的语言回复，适合老年人阅读。直接、坚决地给出回复。内容要口语化，生动，适老化。

回复格式：
判定：[可信/需谨慎/不可信]
一句话总结：[用一句简单的话概括这篇文章的可信度]
详细分析：[分点说明你的判断依据，每点用简单的话解释]"""

        val request = DeepSeekRequest(
            model = "deepseek-chat",
            messages = listOf(DeepSeekMessage(role = "user", content = prompt)),
            maxTokens = 2000,
            stream = false
        )

        val response = client.preparePost(deepSeekUrl) {
            contentType(ContentType.Application.Json)
            header("Authorization", "Bearer $apiKey")
            setBody(request)
        }.execute { httpResponse ->
            if (!httpResponse.status.isSuccess()) {
                val error = httpResponse.bodyAsText()
                throw Exception("AI 分析失败: $error")
            }
            httpResponse.bodyAsText()
        }

        val deepSeekResponse = jsonParser.decodeFromString<DeepSeekResponse>(response)
        val llmContent = deepSeekResponse.choices.firstOrNull()?.message?.content
            ?: throw Exception("AI 未返回分析结果")

        return parseLLMResponse(llmContent, content)
    }

    /**
     * Parse LLM response into AnalyzeResponse
     */
    private fun parseLLMResponse(llmContent: String, originalContent: String): AnalyzeResponse {
        val lines = llmContent.lines()
        var verdict = "caution"
        var verdictEmoji = "⚠️"
        var summary = ""
        var details = ""
        var inDetails = false

        for (line in lines) {
            val trimmedLine = line.trim()
            when {
                trimmedLine.startsWith("判定：") || trimmedLine.startsWith("判定:") -> {
                    val verdictText = trimmedLine.substringAfter("：").substringAfter(":").trim()
                    when {
                        verdictText.contains("可信") && !verdictText.contains("不可信") -> {
                            verdict = "reliable"
                            verdictEmoji = "✅"
                        }
                        verdictText.contains("不可信") || verdictText.contains("谣言") -> {
                            verdict = "misleading"
                            verdictEmoji = "❌"
                        }
                        else -> {
                            verdict = "caution"
                            verdictEmoji = "⚠️"
                        }
                    }
                }
                trimmedLine.startsWith("一句话总结：") || trimmedLine.startsWith("一句话总结:") -> {
                    summary = trimmedLine.substringAfter("：").substringAfter(":").trim()
                    inDetails = false
                }
                trimmedLine.startsWith("详细分析：") || trimmedLine.startsWith("详细分析:") -> {
                    details = trimmedLine.substringAfter("：").substringAfter(":").trim()
                    inDetails = true
                }
                inDetails && trimmedLine.isNotEmpty() -> {
                    details += "\n$trimmedLine"
                }
            }
        }

        // Fallback if parsing failed
        if (summary.isEmpty() && details.isEmpty()) {
            summary = "AI 分析完成"
            details = llmContent
        }

        val title = originalContent.take(50).let {
            if (it.length == 50) "$it..." else it
        }

        return AnalyzeResponse(
            title = title,
            verdict = verdict,
            verdictEmoji = verdictEmoji,
            summary = summary,
            details = details.trim(),
            originalText = originalContent.take(500) + if (originalContent.length > 500) "..." else ""
        )
    }

    /**
     * Main analyze function - handles both URL and direct text
     */
    @Throws(Exception::class)
    suspend fun analyze(text: String): AnalyzeResponse {
        val isUrl = text.startsWith("http://") || text.startsWith("https://")

        return if (isUrl) {
            if (text.contains("mp.weixin.qq.com")) {
                val (title, content, author) = extractWeChatArticle(text)
                val response = analyzeWithLLM(title, content, author)
                response.copy(title = title)
            } else {
                throw Exception("目前仅支持微信公众号文章链接")
            }
        } else {
            // Direct text analysis
            analyzeWithLLM("用户提供的内容", text, "用户输入")
        }
    }

    /**
     * Stream chat response directly from DeepSeek API
     */
    @Throws(Exception::class)
    fun chatStream(request: ChatRequest): Flow<Pair<String, String>> = flow {
        val systemPrompt = """
你是一位帮助老年人识别网络虚假信息的贴心助手"慧眼"。
你之前已经分析过这篇文章：
标题：${request.title ?: "未知"}
原文摘要：${request.originalText?.take(500) ?: "无"}

之前的分析结果：
${request.analysisSummary ?: "无"}
${request.analysisDetails ?: "无"}

现在的任务是回答用户关于这篇文章的后续提问。
请保持语气亲切、耐心，像一位靠谱的晚辈在给长辈解释。
回答要通俗易懂，不要用复杂的术语。
如果是谣言，要温和但坚定地提醒长辈不要相信。

重要提示：
1. 直接回复用户的内容，不要在开头加"(温和地)"或"(认真地)"之类的语气描述。
2. 不要重复"你好"或自我介绍，直接针对问题回答。
"""

        val messages = mutableListOf(DeepSeekMessage(role = "system", content = systemPrompt))
        for (msg in request.messages) {
            messages.add(DeepSeekMessage(role = msg.role, content = msg.content))
        }

        val deepSeekRequest = DeepSeekRequest(
            model = "deepseek-reasoner",
            messages = messages,
            maxTokens = 2000,
            stream = true
        )

        client.preparePost(deepSeekUrl) {
            contentType(ContentType.Application.Json)
            header("Authorization", "Bearer $apiKey")
            setBody(deepSeekRequest)
        }.execute { response ->
            if (!response.status.isSuccess()) {
                throw Exception("请求失败: ${response.status}")
            }

            val channel = response.bodyAsChannel()

            while (!channel.isClosedForRead) {
                val line = channel.readUTF8Line() ?: break

                if (line.startsWith("data:")) {
                    val data = line.removePrefix("data:").trim()
                    if (data == "[DONE]") break

                    try {
                        val chunk = jsonParser.decodeFromString<DeepSeekResponse>(data)
                        val delta = chunk.choices.firstOrNull()?.delta

                        delta?.reasoningContent?.let { text ->
                            if (text.isNotEmpty()) emit(Pair("reasoning", text))
                        }
                        delta?.content?.let { text ->
                            if (text.isNotEmpty()) emit(Pair("content", text))
                        }
                    } catch (e: Exception) {
                        // Skip malformed chunks
                    }
                }
            }
        }
    }
}
