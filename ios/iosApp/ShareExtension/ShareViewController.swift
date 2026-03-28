//
//  ShareViewController.swift
//  ShareExtension
//
//  Created by 王思成 on 2025/12/29.
//

import UIKit
import UniformTypeIdentifiers

class ShareViewController: UIViewController {

    // IMPORTANT: Must match the App Group ID configured in Xcode
    let appGroupIdentifier = "group.com.wiselens.computerization"
    let sharedKey = "sharedURL"
    let urlScheme = "mediafilter-kmp"

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor.black.withAlphaComponent(0.3)
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        handleSharedContent()
    }

    private func handleSharedContent() {
        guard let extensionContext = self.extensionContext,
              let inputItems = extensionContext.inputItems as? [NSExtensionItem] else {
            dismissWithError(message: "No content found")
            return
        }

        for item in inputItems {
            guard let attachments = item.attachments else { continue }

            for attachment in attachments {
                // Log available types for debugging
                let types = attachment.registeredTypeIdentifiers
                NSLog("[ShareExtension] Available types: \(types)")

                // PRIORITY 1: Handle property list (Safari preprocessing) - check this FIRST
                if attachment.hasItemConformingToTypeIdentifier(UTType.propertyList.identifier) {
                    NSLog("[ShareExtension] Using propertyList handler")
                    attachment.loadItem(forTypeIdentifier: UTType.propertyList.identifier) { [weak self] data, error in
                        guard let self = self else { return }

                        if let dict = data as? NSDictionary,
                           let results = dict[NSExtensionJavaScriptPreprocessingResultsKey] as? NSDictionary,
                           let url = results["baseURI"] as? String {
                            NSLog("[ShareExtension] Got baseURI from JS: \(url)")
                            self.saveAndRedirect(urlString: url)
                        } else {
                            NSLog("[ShareExtension] propertyList failed, trying URL fallback")
                            // Fallback to URL type
                            self.tryURLType(attachment: attachment)
                        }
                    }
                    return
                }

                // PRIORITY 2: Handle URLs
                if attachment.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
                    NSLog("[ShareExtension] Using URL handler")
                    tryURLType(attachment: attachment)
                    return
                }

                // PRIORITY 3: Handle plain text (might contain URL)
                if attachment.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                    NSLog("[ShareExtension] Using plainText handler")
                    attachment.loadItem(forTypeIdentifier: UTType.plainText.identifier) { [weak self] data, error in
                        guard let self = self else { return }

                        if let text = data as? String {
                            NSLog("[ShareExtension] Got text: \(text)")
                            self.saveAndRedirect(urlString: text)
                        } else if let error = error {
                            DispatchQueue.main.async {
                                self.dismissWithError(message: error.localizedDescription)
                            }
                        }
                    }
                    return
                }
            }
        }

        dismissWithError(message: "Unsupported content type")
    }

    private func tryURLType(attachment: NSItemProvider) {
        attachment.loadItem(forTypeIdentifier: UTType.url.identifier) { [weak self] data, error in
            guard let self = self else { return }

            if let url = data as? URL {
                NSLog("[ShareExtension] Got URL: \(url.absoluteString)")
                self.saveAndRedirect(urlString: url.absoluteString)
            } else if let error = error {
                DispatchQueue.main.async {
                    self.dismissWithError(message: error.localizedDescription)
                }
            }
        }
    }

    private func saveAndRedirect(urlString: String) {
        // Save to App Group UserDefaults
        if let userDefaults = UserDefaults(suiteName: appGroupIdentifier) {
            userDefaults.set(urlString, forKey: sharedKey)
            userDefaults.synchronize()
        }

        // Open main app via URL scheme
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }

            let encodedURL = urlString.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? urlString
            if let url = URL(string: "\(self.urlScheme)://share?url=\(encodedURL)") {
                self.openURL(url)
            }

            self.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
        }
    }

    private func openURL(_ url: URL) {
        var responder: UIResponder? = self
        while responder != nil {
            if let application = responder as? UIApplication {
                application.open(url, options: [:], completionHandler: nil)
                return
            }
            responder = responder?.next
        }
    }

    private func dismissWithError(message: String) {
        DispatchQueue.main.async { [weak self] in
            let alert = UIAlertController(
                title: "Error",
                message: message,
                preferredStyle: .alert
            )
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                self?.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
            })
            self?.present(alert, animated: true)
        }
    }
}
