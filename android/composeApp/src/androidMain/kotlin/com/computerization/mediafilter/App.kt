package com.computerization.mediafilter

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.computerization.mediafilter.data.AnalyzeResponse
import com.computerization.mediafilter.ui.MainScreen
import com.computerization.mediafilter.ui.ResultScreen
import kotlinx.coroutines.flow.SharedFlow

@Composable
fun App(
    initialSharedText: String?,
    sharedTextFlow: SharedFlow<String>
) {
    val viewModel = remember { SharedViewModel() }
    var currentResult by remember { mutableStateOf<AnalyzeResponse?>(null) }

    if (currentResult != null) {
        ResultScreen(
            result = currentResult!!,
            viewModel = viewModel,
            onBack = { currentResult = null }
        )
    } else {
        MainScreen(
            viewModel = viewModel,
            initialSharedText = initialSharedText,
            sharedTextFlow = sharedTextFlow,
            onNavigateToResult = { result -> currentResult = result }
        )
    }
}
