//
//  iosAppApp.swift
//  iosApp
//
//  Created by 王思成 on 2025/12/24.
//

import SwiftUI
import Combine

@main
struct iosAppApp: App {
    @StateObject private var sharedURLManager = SharedURLManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(sharedURLManager)
                .onOpenURL { url in
                    handleIncomingURL(url)
                }
                .onAppear {
                    // Check for shared content when app launches
                    sharedURLManager.checkForSharedContent()
                }
        }
    }

    private func handleIncomingURL(_ url: URL) {
        // Handle URL scheme: mediafilter-kmp://share?url=...
        guard url.scheme == "mediafilter-kmp",
              url.host == "share",
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let queryItems = components.queryItems,
              let sharedURL = queryItems.first(where: { $0.name == "url" })?.value else {
            return
        }

        sharedURLManager.setSharedURL(sharedURL)
    }
}

/// Manages shared URL state across the app
class SharedURLManager: ObservableObject {
    @Published var sharedURL: String?
    @Published var shouldAutoAnalyze: Bool = false

    private let appGroupIdentifier = "group.com.wiselens.computerization"
    private let sharedKey = "sharedURL"

    func checkForSharedContent() {
        guard let userDefaults = UserDefaults(suiteName: appGroupIdentifier),
              let savedURL = userDefaults.string(forKey: sharedKey) else {
            return
        }

        // Clear the saved URL
        userDefaults.removeObject(forKey: sharedKey)
        userDefaults.synchronize()

        // Set the shared URL
        setSharedURL(savedURL)
    }

    func setSharedURL(_ url: String) {
        DispatchQueue.main.async {
            self.sharedURL = url
            self.shouldAutoAnalyze = true
        }
    }

    func clearSharedURL() {
        sharedURL = nil
        shouldAutoAnalyze = false
    }
}
