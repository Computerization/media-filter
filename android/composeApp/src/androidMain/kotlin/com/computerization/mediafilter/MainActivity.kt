package com.computerization.mediafilter

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.computerization.mediafilter.theme.MediaFilterTheme
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

class MainActivity : ComponentActivity() {

    private val _sharedTextFlow = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val sharedTextFlow = _sharedTextFlow.asSharedFlow()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val initialSharedText = handleShareIntent(intent)

        setContent {
            MediaFilterTheme {
                App(
                    initialSharedText = initialSharedText,
                    sharedTextFlow = sharedTextFlow
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShareIntent(intent)?.let { text ->
            _sharedTextFlow.tryEmit(text)
        }
    }

    private fun handleShareIntent(intent: Intent): String? {
        if (intent.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            return intent.getStringExtra(Intent.EXTRA_TEXT)
        }
        return null
    }
}
