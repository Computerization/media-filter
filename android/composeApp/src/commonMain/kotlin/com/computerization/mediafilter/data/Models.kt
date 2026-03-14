package com.computerization.mediafilter.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AnalyzeRequest(
    val url: String? = null,
    val text: String? = null
)

@Serializable
data class AnalyzeResponse(
    val title: String,
    val verdict: String, // "reliable", "caution", "misleading"
    @SerialName("verdict_emoji") val verdictEmoji: String,
    val summary: String,
    val details: String,
    @SerialName("original_text") val originalText: String? = null
)

@Serializable
data class ErrorResponse(
    val detail: String
)

// --- Chat Models ---

@Serializable
data class ChatMessage(
    val role: String, // "user" or "assistant"
    val content: String
)

@Serializable
data class ChatRequest(
    val messages: List<ChatMessage>,
    val title: String? = null,
    @SerialName("original_text") val originalText: String? = null,
    @SerialName("analysis_summary") val analysisSummary: String? = null,
    @SerialName("analysis_details") val analysisDetails: String? = null
)

@Serializable
data class ChatResponse(
    val response: String,
    val reasoning: String? = null
)

@Serializable
data class ChatStreamChunk(
    val text: String? = null,
    val error: String? = null
)