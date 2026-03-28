import { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  AppState,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import { router } from "expo-router";
import { analyzeContent, AnalyzeResponse } from "@/lib/api";

// Only import share intent on native platforms
let useShareIntent: () => { hasShareIntent: boolean; shareIntent: any; resetShareIntent: () => void };
if (Platform.OS !== "web") {
  useShareIntent = require("expo-share-intent").useShareIntent;
} else {
  useShareIntent = () => ({ hasShareIntent: false, shareIntent: null, resetShareIntent: () => {} });
}

export default function HomeScreen() {
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const appState = useRef(AppState.currentState);
  const lastClipboard = useRef("");
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent();

  const handleAnalyzeWithText = useCallback(async (text: string) => {
    if (!text.trim()) return;

    setIsLoading(true);
    try {
      const isUrl = text.startsWith("http://") || text.startsWith("https://");
      const result: AnalyzeResponse = await analyzeContent(
        isUrl ? text : undefined,
        isUrl ? undefined : text
      );
      router.push({
        pathname: "/result",
        params: {
          title: result.title,
          verdict: result.verdict,
          verdict_emoji: result.verdict_emoji,
          summary: result.summary,
          details: result.details,
        },
      });
    } catch (error) {
      Alert.alert(
        "分析失败",
        error instanceof Error ? error.message : "请检查网络连接后重试"
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle shared content from other apps (Share Extension)
  useEffect(() => {
    if (hasShareIntent && shareIntent) {
      const sharedContent = shareIntent.webUrl || shareIntent.text || "";
      if (sharedContent) {
        setInputText(sharedContent);
        if (sharedContent.startsWith("http")) {
          handleAnalyzeWithText(sharedContent);
        }
        resetShareIntent();
      }
    }
  }, [hasShareIntent, shareIntent, handleAnalyzeWithText, resetShareIntent]);

  // Auto-detect clipboard when app becomes active (fallback)
  useEffect(() => {
    const checkClipboard = async () => {
      try {
        const text = await Clipboard.getStringAsync();
        if (
          text &&
          text !== lastClipboard.current &&
          (text.includes("mp.weixin.qq.com") || text.includes("weixin.qq.com"))
        ) {
          lastClipboard.current = text;
          Alert.alert("检测到微信文章链接", "是否要分析这篇文章？", [
            { text: "取消", style: "cancel" },
            {
              text: "开始分析",
              onPress: () => {
                setInputText(text);
                handleAnalyzeWithText(text);
              },
            },
          ]);
        }
      } catch {
        // Ignore clipboard errors
      }
    };

    checkClipboard();

    const subscription = AppState.addEventListener("change", (nextAppState) => {
      if (
        appState.current.match(/inactive|background/) &&
        nextAppState === "active"
      ) {
        checkClipboard();
      }
      appState.current = nextAppState;
    });

    return () => subscription.remove();
  }, [handleAnalyzeWithText]);

  const handlePaste = async () => {
    try {
      const text = await Clipboard.getStringAsync();
      if (text) {
        setInputText(text);
      } else {
        Alert.alert("提示", "剪贴板中没有内容");
      }
    } catch {
      Alert.alert("错误", "无法读取剪贴板");
    }
  };

  const handleAnalyze = () => {
    const text = inputText.trim();
    if (!text) {
      Alert.alert("提示", "请先粘贴文章链接或输入文字内容");
      return;
    }
    handleAnalyzeWithText(text);
  };

  const handleClear = () => {
    setInputText("");
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Instructions */}
        <View style={styles.instructionBox}>
          <Text style={styles.instructionTitle}>使用说明</Text>
          <Text style={styles.instructionText}>
            1. 在微信中打开可疑文章{"\n"}
            2. 点击右上角"..." → 分享{"\n"}
            3. 选择"慧眼"即可分析
          </Text>
        </View>

        {/* Input Area */}
        <Text style={styles.label}>文章链接或文字内容：</Text>
        <TextInput
          style={styles.input}
          multiline
          numberOfLines={4}
          placeholder='点击下方"粘贴"按钮，或直接在此输入内容...'
          placeholderTextColor="#999"
          value={inputText}
          onChangeText={setInputText}
          textAlignVertical="top"
        />

        {/* Action Buttons */}
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.button, styles.pasteButton]}
            onPress={handlePaste}
          >
            <Text style={styles.buttonText}>📋 粘贴</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.clearButton]}
            onPress={handleClear}
          >
            <Text style={styles.buttonText}>🗑️ 清空</Text>
          </TouchableOpacity>
        </View>

        {/* Analyze Button */}
        <TouchableOpacity
          style={[
            styles.analyzeButton,
            isLoading && styles.analyzeButtonDisabled,
          ]}
          onPress={handleAnalyze}
          disabled={isLoading}
        >
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator color="#fff" size="small" />
              <Text style={styles.analyzeButtonText}>正在分析...</Text>
            </View>
          ) : (
            <Text style={styles.analyzeButtonText}>🔍 开始分析</Text>
          )}
        </TouchableOpacity>

        {/* Footer */}
        <Text style={styles.footer}>
          由 Computerization 社团开发{"\n"}
          帮助长辈识别网络虚假信息
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F5",
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  instructionBox: {
    backgroundColor: "#E3F2FD",
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: "#4A90D9",
  },
  instructionTitle: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#1565C0",
    marginBottom: 8,
  },
  instructionText: {
    fontSize: 16,
    color: "#333",
    lineHeight: 26,
  },
  label: {
    fontSize: 18,
    fontWeight: "600",
    color: "#333",
    marginBottom: 8,
  },
  input: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    fontSize: 17,
    minHeight: 120,
    borderWidth: 2,
    borderColor: "#E0E0E0",
    color: "#333",
  },
  buttonRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 16,
  },
  button: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  pasteButton: {
    backgroundColor: "#4A90D9",
  },
  clearButton: {
    backgroundColor: "#9E9E9E",
  },
  buttonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },
  analyzeButton: {
    backgroundColor: "#22C55E",
    paddingVertical: 18,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 20,
    shadowColor: "#22C55E",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  analyzeButtonDisabled: {
    backgroundColor: "#9CA3AF",
    shadowOpacity: 0,
  },
  analyzeButtonText: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "bold",
  },
  loadingContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  footer: {
    textAlign: "center",
    color: "#9CA3AF",
    fontSize: 14,
    marginTop: 32,
    lineHeight: 22,
  },
});
