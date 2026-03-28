package com.computerization.mediafilter

import com.computerization.mediafilter.data.AnalyzeResponse
import com.computerization.mediafilter.data.ChatRequest
import com.computerization.mediafilter.network.MediaFilterApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SharedViewModel {
    private val api = MediaFilterApi()
    private val scope = MainScope()

    // Callback interface for Swift
    // On success: response is not null, error is null
    // On failure: response is null, error is not null
    fun analyzeContent(text: String, callback: (AnalyzeResponse?, String?) -> Unit) {
        scope.launch {
            try {
                // Switch to IO thread for network call
                val result = withContext(Dispatchers.IO) {
                    api.analyze(text)
                }
                // Call callback on Main thread
                callback(result, null)
            } catch (e: Exception) {
                callback(null, e.message ?: "Unknown error")
            }
        }
    }

    fun chatStream(
        request: ChatRequest,
        onChunk: (String, String) -> Unit, // (event, text)
        onComplete: () -> Unit,
        onError: (String) -> Unit
    ) {
        scope.launch {
            try {
                api.chatStream(request).collect { pair ->
                    onChunk(pair.first, pair.second)
                }
                onComplete()
            } catch (e: Exception) {
                onError(e.message ?: "Unknown streaming error")
            }
        }
    }
}
