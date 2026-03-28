import SwiftUI
import SharedLogic

// MARK: - Theme Colors
struct AppColors {
    @Environment(\.colorScheme) var colorScheme

    static func cardBackground(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? Color(white: 0.15) : Color.white
    }

    static func secondaryBackground(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? Color(white: 0.1) : Color(white: 0.97)
    }

    static func inputBackground(_ colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? Color(white: 0.12) : Color.white
    }

    static let primaryBlue = Color(red: 0.29, green: 0.56, blue: 0.85)
    static let accentGreen = Color(red: 0.2, green: 0.78, blue: 0.35)
    static let warningOrange = Color(red: 1.0, green: 0.6, blue: 0.0)
    static let dangerRed = Color(red: 0.9, green: 0.25, blue: 0.2)
}

// MARK: - Local Chat Model
struct ChatBubble: Identifiable {
    var id = UUID()
    let role: String // "user" or "assistant"
    var content: String
    var reasoning: String? = nil
}

// MARK: - Chat Bubble View
struct ChatBubbleView: View {
    let msg: ChatBubble
    @Environment(\.colorScheme) var colorScheme
    @State private var isReasoningExpanded: Bool = false
    
    var body: some View {
        HStack(alignment: .top) {
            if msg.role == "user" { Spacer(minLength: 50) }
            
            VStack(alignment: msg.role == "user" ? .trailing : .leading, spacing: 6) {
                // Reasoning Section (DeepSeek Thought)
                if let reasoning = msg.reasoning, !reasoning.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Button(action: { withAnimation { isReasoningExpanded.toggle() } }) {
                            HStack(spacing: 6) {
                                Image(systemName: "sparkles")
                                    .font(.caption2)
                                Text(isReasoningExpanded ? "收起思考过程" : "查看深度思考")
                                    .font(.caption2.weight(.medium))
                                Image(systemName: isReasoningExpanded ? "chevron.up" : "chevron.down")
                                    .font(.caption2)
                            }
                            .foregroundColor(AppColors.primaryBlue)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(AppColors.primaryBlue.opacity(0.1))
                            .cornerRadius(12)
                        }
                        
                        if isReasoningExpanded {
                            ScrollView {
                                Text(reasoning)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .padding(10)
                            }
                            .frame(maxHeight: 150) // Limit height
                            .background(Color.gray.opacity(0.05))
                            .cornerRadius(8)
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }
                    }
                    .padding(.bottom, 4)
                    .onAppear {
                        // Auto-expand if reasoning is not empty when appearing (useful for streaming)
                        if !reasoning.isEmpty { isReasoningExpanded = true }
                    }
                    .onChange(of: msg.reasoning) { _, newValue in
                        // Keep expanded if reasoning is growing
                        if let val = newValue, !val.isEmpty, !isReasoningExpanded {
                            withAnimation { isReasoningExpanded = true }
                        }
                    }
                }
                
                // Main Content
                if !msg.content.isEmpty {
                    Text(LocalizedStringKey(msg.content)) // Using LocalizedStringKey for basic Markdown
                        .padding(14)
                        .background(
                            msg.role == "user" 
                            ? AppColors.primaryBlue 
                            : AppColors.cardBackground(colorScheme)
                        )
                        .foregroundColor(msg.role == "user" ? .white : .primary)
                        .cornerRadius(18)
                        .shadow(color: Color.black.opacity(0.05), radius: 3)
                }
            }
            
            if msg.role == "assistant" { Spacer(minLength: 50) }
        }
    }
}

// MARK: - Main Content View
struct ContentView: View {
    @EnvironmentObject var sharedURLManager: SharedURLManager
    @Environment(\.colorScheme) var colorScheme
    @State private var inputText: String = ""
    @State private var isLoading: Bool = false
    @State private var showResult: Bool = false
    @State private var result: AnalyzeResponse? = nil
    @State private var errorMessage: String? = nil
    @State private var animateGradient: Bool = false
    @FocusState private var isInputFocused: Bool

    let viewModel = SharedViewModel()

    var body: some View {
        NavigationStack {
            ZStack {
                // Animated gradient background (Restored Quality)
                LinearGradient(
                    colors: [
                        AppColors.primaryBlue.opacity(colorScheme == .dark ? 0.3 : 0.1),
                        colorScheme == .dark ? Color.black : Color.white
                    ],
                    startPoint: animateGradient ? .topLeading : .topTrailing,
                    endPoint: animateGradient ? .bottomTrailing : .bottomLeading
                )
                .ignoresSafeArea()
                .onAppear {
                    withAnimation(.easeInOut(duration: 3).repeatForever(autoreverses: true)) {
                        animateGradient.toggle()
                    }
                }

                ScrollView {
                    VStack(spacing: 24) {
                        // Header Card
                        headerCard

                        // Input Card
                        inputCard

                        // Action Buttons
                        actionButtons

                        // Analyze Button
                        analyzeButton

                        // Connection Hint
                        connectionHintView

                        // Footer
                        footerView
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
                .scrollDismissesKeyboard(.immediately)
                .onTapGesture {
                    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                }
            }
            .ignoresSafeArea(.keyboard)
            .navigationTitle("慧眼")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(AppColors.primaryBlue, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .navigationDestination(isPresented: $showResult) {
                if let res = result {
                    ResultView(result: res, viewModel: viewModel)
                }
            }
            .alert("错误", isPresented: Binding(get: { errorMessage != nil }, set: { _ in errorMessage = nil })) {
                Button("确定", role: .cancel) { }
            } message: {
                Text(errorMessage ?? "")
            }
            .onChange(of: sharedURLManager.sharedURL) { _, newValue in
                if let url = newValue, sharedURLManager.shouldAutoAnalyze {
                    inputText = url
                    sharedURLManager.clearSharedURL()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        analyze()
                    }
                }
            }
            .onAppear {
                if let url = sharedURLManager.sharedURL, sharedURLManager.shouldAutoAnalyze {
                    inputText = url
                    sharedURLManager.clearSharedURL()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        analyze()
                    }
                }
            }
        }
    }

    // MARK: - Header Card
    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "info.circle.fill")
                    .font(.title2)
                    .foregroundColor(AppColors.primaryBlue)
                Text("使用说明")
                    .font(.headline)
                    .fontWeight(.semibold)
            }

            VStack(alignment: .leading, spacing: 8) {
                instructionRow(number: "1", text: "在微信中打开可疑文章")
                instructionRow(number: "2", text: "点击右上角 ··· → 分享")
                instructionRow(number: "3", text: "选择「慧眼」即可自动分析")
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.cardBackground(colorScheme))
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(colorScheme == .dark ? 0.3 : 0.08), radius: 10, x: 0, y: 4)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(AppColors.primaryBlue.opacity(0.3), lineWidth: 1)
        )
    }

    private func instructionRow(number: String, text: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Text(number)
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.white)
                .frame(width: 22, height: 22)
                .background(AppColors.primaryBlue)
                .clipShape(Circle())

            Text(text)
                .font(.subheadline)
                .foregroundColor(.primary)
        }
    }

    // MARK: - Input Card
    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "doc.text.fill")
                    .foregroundColor(AppColors.primaryBlue)
                Text("文章链接或文字内容")
                    .font(.headline)
                    .fontWeight(.semibold)
            }

            ZStack(alignment: .topLeading) {
                if inputText.isEmpty {
                    Text("请粘贴微信文章链接或输入需要鉴别的文字...")
                        .foregroundColor(.gray.opacity(0.6))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 14)
                }

                TextEditor(text: $inputText)
                    .frame(minHeight: 120, maxHeight: 200)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(AppColors.inputBackground(colorScheme))
                    .focused($isInputFocused)
            }
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.gray.opacity(0.2), lineWidth: 1)
            )
        }
        .padding(16)
        .background(AppColors.cardBackground(colorScheme))
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(colorScheme == .dark ? 0.3 : 0.08), radius: 10, x: 0, y: 4)
    }

    // MARK: - Action Buttons
    private var actionButtons: some View {
        HStack(spacing: 12) {
            Button(action: {
                withAnimation(.spring(response: 0.3)) {
                    if let clipboard = UIPasteboard.general.string {
                        inputText = clipboard
                    }
                }
            }) {
                HStack {
                    Image(systemName: "doc.on.clipboard.fill")
                    Text("粘贴")
                }
                .font(.subheadline.weight(.semibold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(AppColors.primaryBlue)
                .foregroundColor(.white)
                .cornerRadius(12)
            }

            Button(action: {
                withAnimation(.spring(response: 0.3)) {
                    inputText = ""
                }
            }) {
                HStack {
                    Image(systemName: "trash.fill")
                    Text("清空")
                }
                .font(.subheadline.weight(.semibold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(colorScheme == .dark ? Color(white: 0.25) : Color(white: 0.9))
                .foregroundColor(colorScheme == .dark ? .white : .primary)
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Analyze Button
    private var analyzeButton: some View {
        Button(action: analyze) {
            HStack(spacing: 10) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.9)
                    Text("正在分析...")
                } else {
                    Image(systemName: "magnifyingglass")
                        .font(.title3)
                    Text("开始分析")
                }
            }
            .font(.title3.weight(.bold))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 18)
            .background(
                LinearGradient(
                    colors: isLoading
                        ? [Color.gray, Color.gray]
                        : [AppColors.accentGreen, AppColors.accentGreen.opacity(0.8)],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .foregroundColor(.white)
            .cornerRadius(16)
            .shadow(color: isLoading ? .clear : AppColors.accentGreen.opacity(0.4), radius: 12, x: 0, y: 6)
        }
        .disabled(isLoading || inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        .scaleEffect(isLoading ? 0.98 : 1.0)
        .animation(.spring(response: 0.3), value: isLoading)
    }

    // MARK: - Footer
    private var connectionHintView: some View {
        HStack(spacing: 8) {
            Image(systemName: "info.circle.fill")
                .font(.caption)
                .foregroundColor(.orange)

            Text("如遇连接问题，请更新至最新版本")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.orange.opacity(0.1))
        .cornerRadius(10)
    }

    private var footerView: some View {
        VStack(spacing: 8) {
            HStack(spacing: 4) {
                Image(systemName: "building.2.fill")
                    .font(.caption2)
                Text("Computerization")
                    .fontWeight(.medium)
            }
            .font(.caption)
            .foregroundColor(.secondary)

            Text("帮助长辈识别网络虚假信息")
                .font(.caption2)
                .foregroundColor(.secondary.opacity(0.8))
        }
        .padding(.top, 16)
        .padding(.bottom, 8)
    }

    // MARK: - Analyze Function
    func analyze() {
        guard !inputText.isEmpty else { return }

        withAnimation(.spring(response: 0.3)) {
            isLoading = true
        }
        errorMessage = nil

        viewModel.analyzeContent(text: inputText) { response, error in
            withAnimation(.spring(response: 0.3)) {
                isLoading = false
            }
            if let err = error {
                errorMessage = err
            } else if let res = response {
                result = res
                showResult = true
            }
        }
    }
}

// MARK: - Result View
struct ResultView: View {
    let result: AnalyzeResponse
    let viewModel: SharedViewModel
    @Environment(\.colorScheme) var colorScheme
    @Environment(\.dismiss) var dismiss
    
    @State private var chatMessages: [ChatBubble] = []
    @State private var chatInput: String = ""
    @State private var isChatLoading: Bool = false
    @State private var scrollOffset: CGFloat = 0
    @State private var appearAnimation = false
    @FocusState private var isChatFocused: Bool
    
    private let topID = "top_of_result"
    private let chatTopID = "chat_start"

    var body: some View {
        ScrollViewReader { proxy in
            ZStack(alignment: .bottom) {
                ScrollView {
                    VStack(spacing: 20) {
                        // Invisible anchor for scrolling to top
                        Color.clear.frame(height: 1).id(topID)
                            .onAppear { appearAnimation = true }

                        // 1. Original Analysis Cards
                        verdictCard
                            .transition(.move(edge: .top).combined(with: .opacity))
                            .background(
                                GeometryReader { geo in
                                    Color.clear
                                        .onChange(of: geo.frame(in: .global).minY) { _, newValue in
                                            DispatchQueue.main.async {
                                                self.scrollOffset = newValue
                                            }
                                        }
                                }
                            )
                        
                        summaryCard
                        detailsCard
                        titleCard

                        // 2. Chat Section Header
                        HStack {
                            Rectangle().frame(height: 1).foregroundColor(.gray.opacity(0.2))
                            Text("向助手提问")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .padding(.horizontal, 8)
                            Rectangle().frame(height: 1).foregroundColor(.gray.opacity(0.2))
                        }
                        .padding(.vertical, 10)
                        .id(chatTopID)

                        // 3. Chat Messages (Bubbles)
                        VStack(spacing: 16) {
                            ChatBubbleView(msg: ChatBubble(role: "assistant", content: "您好！我是您的助手。关于这篇文章，我已经为您做好了分析。如果有任何不明白的地方，请随时问我！"))
                            
                            ForEach(chatMessages) { msg in
                                ChatBubbleView(msg: msg)
                            }
                            
                            if isChatLoading {
                                HStack {
                                    ProgressView().padding().background(AppColors.cardBackground(colorScheme))
                                    Spacer()
                                }.padding(.leading, 10)
                            }
                        }
                        .padding(.bottom, 100)
                    }
                    .padding(20)
                }
                .scrollDismissesKeyboard(.immediately)
                .onTapGesture {
                    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                }
                .onChange(of: chatMessages.count) {
                    withAnimation {
                        proxy.scrollTo(chatMessages.last?.id, anchor: .bottom)
                    }
                }

                // 5. Chat Input Bar
                VStack {
                    Spacer()
                    chatInputBar
                }
            }
            .background(AppColors.secondaryBackground(colorScheme).ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Group {
                        if scrollOffset < 50 {
                            // Liquid Glass Pill
                            Button(action: {
                                withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                                    proxy.scrollTo(topID, anchor: .top)
                                }
                            }) {
                                HStack(spacing: 8) {
                                    Text(result.verdictEmoji)
                                        .font(.system(size: 14))
                                    
                                    VStack(alignment: .leading, spacing: 0) {
                                        Text(result.title)
                                            .font(.system(size: 12, weight: .bold))
                                            .lineLimit(1)
                                            .truncationMode(.tail)
                                            .frame(maxWidth: 100, alignment: .leading)
                                            .foregroundColor(.primary)
                                        Text(getVerdictText())
                                            .font(.system(size: 9, weight: .semibold))
                                            .foregroundColor(getVerdictColor())
                                    }
                                    
                                    Image(systemName: "chevron.up.circle.fill")
                                        .font(.system(size: 12))
                                        .foregroundStyle(.secondary) // Native vibrancy
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(.ultraThinMaterial, in: Capsule()) // True Liquid Glass
                                .overlay(
                                    Capsule()
                                        .stroke(.white.opacity(0.1), lineWidth: 0.5) // Subtle edge highlight
                                )
                                .shadow(color: Color.black.opacity(0.05), radius: 10, x: 0, y: 5)
                            }
                            .fixedSize() // Prevent stretching
                            .transition(.move(edge: .top).combined(with: .opacity))
                        } else {
                            Text("详细报告")
                                .font(.headline)
                                .transition(.opacity)
                        }
                    }
                    .animation(.spring(response: 0.3, dampingFraction: 0.7), value: scrollOffset < 50)
                }
            }
        }
        .navigationBarBackButtonHidden(false)
    }

    // MARK: - Chat Input Bar
    private var chatInputBar: some View {
        VStack(spacing: 0) {
            Divider()
            HStack(spacing: 12) {
                TextField("问问助手...", text: $chatInput)
                    .padding(12)
                    .background(AppColors.inputBackground(colorScheme))
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                    .focused($isChatFocused)
                
                Button(action: sendChatMessage) {
                    Image(systemName: "paperplane.fill")
                        .font(.title3)
                        .foregroundColor(.white)
                        .frame(width: 44, height: 44)
                        .background(chatInput.isEmpty ? Color.gray : AppColors.primaryBlue)
                        .clipShape(Circle())
                }
                .disabled(chatInput.isEmpty || isChatLoading)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(AppColors.cardBackground(colorScheme))
        }
    }

    // MARK: - Actions
    private func sendChatMessage() {
        let text = chatInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        
        // 1. Add User Message
        let userMsg = ChatBubble(role: "user", content: text)
        chatMessages.append(userMsg)
        chatInput = ""
        
        // 2. Add Empty Assistant Message for Streaming
        let assistantMsgId = UUID()
        let initialAssistantMsg = ChatBubble(id: assistantMsgId, role: "assistant", content: "", reasoning: "")
        chatMessages.append(initialAssistantMsg)
        
        isChatLoading = true
        
        // Convert current history to KMP Models
        let kmpMessages = chatMessages.dropLast().map { SharedLogic.ChatMessage(role: $0.role, content: $0.content) }
        let request = SharedLogic.ChatRequest(
            messages: kmpMessages,
            title: result.title,
            originalText: result.originalText,
            analysisSummary: result.summary,
            analysisDetails: result.details
        )
        
        viewModel.chatStream(request: request) { event, chunk in
            // UI updates must happen on main thread (KMP callback is usually main thread but let's be safe)
            DispatchQueue.main.async {
                if let index = chatMessages.firstIndex(where: { $0.id == assistantMsgId }) {
                    if event == "reasoning" {
                        chatMessages[index].reasoning = (chatMessages[index].reasoning ?? "") + chunk
                    } else if event == "content" {
                        chatMessages[index].content = chatMessages[index].content + chunk
                    }
                }
            }
        } onComplete: {
            DispatchQueue.main.async {
                isChatLoading = false
            }
        } onError: { error in
            DispatchQueue.main.async {
                isChatLoading = false
                if let index = chatMessages.firstIndex(where: { $0.id == assistantMsgId }) {
                    chatMessages[index].content = "抱歉，出错了：\(error)"
                }
            }
        }
    }

    // MARK: - Sub-cards (Existing)
    private var verdictCard: some View {
        HStack(spacing: 16) {
            Text(result.verdictEmoji)
                .font(.system(size: 56))

            VStack(alignment: .leading, spacing: 4) {
                Text("判定结果")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(getVerdictText())
                    .font(.title.weight(.bold))
                    .foregroundColor(getVerdictColor())
            }
            Spacer()
        }
        .padding(20)
        .background(
            LinearGradient(
                colors: [getVerdictColor().opacity(0.15), getVerdictColor().opacity(0.05)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .background(AppColors.cardBackground(colorScheme))
        .cornerRadius(20)
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(getVerdictColor().opacity(0.3), lineWidth: 2))
        .shadow(color: getVerdictColor().opacity(0.2), radius: 10, x: 0, y: 4)
    }

    private var summaryCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "text.alignleft").foregroundColor(AppColors.primaryBlue)
                Text("简要说明").font(.headline.weight(.semibold))
            }
            markdownText(result.summary).font(.body)
                .lineSpacing(4)
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.cardBackground(colorScheme)).cornerRadius(16)
        .shadow(color: Color.black.opacity(colorScheme == .dark ? 0.3 : 0.08), radius: 10, x: 0, y: 4)
    }

    private var detailsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "doc.text.magnifyingglass").foregroundColor(AppColors.primaryBlue)
                Text("详细分析").font(.headline.weight(.semibold))
            }
            markdownText(result.details).font(.body)
                .lineSpacing(4)
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.cardBackground(colorScheme)).cornerRadius(16)
        .shadow(color: Color.black.opacity(colorScheme == .dark ? 0.3 : 0.08), radius: 10, x: 0, y: 4)
    }

    private var titleCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "newspaper.fill").foregroundColor(AppColors.primaryBlue)
                Text("原文标题").font(.headline.weight(.semibold))
            }
            Text(result.title).font(.subheadline).foregroundColor(.secondary)
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.cardBackground(colorScheme)).cornerRadius(16)
        .shadow(color: Color.black.opacity(colorScheme == .dark ? 0.3 : 0.08), radius: 10, x: 0, y: 4)
    }

    // MARK: - Helpers
    func markdownText(_ text: String) -> Text {
        do {
            let attributedString = try AttributedString(markdown: text, options: AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace))
            return Text(attributedString)
        } catch {
            return Text(text)
        }
    }

    func getVerdictText() -> String {
        switch result.verdict {
        case "reliable": return "信息可信"
        case "misleading": return "不可信/谣言"
        default: return "需要谨慎"
        }
    }

    func getVerdictColor() -> Color {
        switch result.verdict {
        case "reliable": return AppColors.accentGreen
        case "misleading": return AppColors.dangerRed
        default: return AppColors.warningOrange
        }
    }
}

// MARK: - Scroll Helper
struct ScrollOffsetPreferenceKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

// MARK: - Preview
#Preview {
    ContentView()
        .environmentObject(SharedURLManager())
}

