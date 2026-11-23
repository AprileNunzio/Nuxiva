import OSLog
import SwiftUI
import WebKit

struct HubWebView: UIViewRepresentable {
    let url: URL
    let anchor: SecCertificate
    let onFailure: @MainActor (String) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(origin: url, anchor: anchor, onFailure: onFailure)
    }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        configuration.limitsNavigationsToAppBoundDomains = false
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        view.isOpaque = false
        view.backgroundColor = .black
        view.scrollView.contentInsetAdjustmentBehavior = .never
        view.allowsBackForwardNavigationGestures = false
        view.isInspectable = false
        view.load(URLRequest(url: url))
        return view
    }

    func updateUIView(_ view: WKWebView, context: Context) {}

    static func dismantleUIView(_ view: WKWebView, coordinator: Coordinator) {
        view.stopLoading()
        view.navigationDelegate = nil
        view.uiDelegate = nil
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        private let origin: URL
        private let anchor: SecCertificate
        private let onFailure: @MainActor (String) -> Void
        private let log = Logger(subsystem: "com.nuxiva.ios", category: "hub")

        init(origin: URL, anchor: SecCertificate, onFailure: @escaping @MainActor (String) -> Void) {
            self.origin = origin
            self.anchor = anchor
            self.onFailure = onFailure
        }

        private func sameOrigin(_ url: URL?) -> Bool {
            guard let url else { return false }
            return url.scheme == "https" && url.host == origin.host && (url.port ?? 443) == (origin.port ?? 443)
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor action: WKNavigationAction
        ) async -> WKNavigationActionPolicy {
            if sameOrigin(action.request.url) || action.request.url?.scheme == "about" {
                return .allow
            }
            log.notice("Blocked navigation outside the server origin")
            return .cancel
        }

        func webView(
            _ webView: WKWebView,
            respondTo challenge: URLAuthenticationChallenge
        ) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
            guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
                  let trust = challenge.protectionSpace.serverTrust else {
                return (.performDefaultHandling, nil)
            }
            guard challenge.protectionSpace.host == origin.host, PinnedTrust.evaluate(trust, anchor: anchor) else {
                onFailure("pin")
                return (.cancelAuthenticationChallenge, nil)
            }
            return (.useCredential, URLCredential(trust: trust))
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: any Error) {
            report(error)
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: any Error) {
            report(error)
        }

        func webView(
            _ webView: WKWebView,
            decideMediaCapturePermissionsFor origin: WKSecurityOrigin,
            initiatedBy frame: WKFrameInfo,
            type: WKMediaCaptureType
        ) async -> WKPermissionDecision {
            .deny
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            nil
        }

        private func report(_ error: any Error) {
            let nsError = error as NSError
            if nsError.domain == NSURLErrorDomain, nsError.code == NSURLErrorCancelled { return }
            log.warning("Hub navigation failed: \(nsError.domain, privacy: .public) \(nsError.code)")
            onFailure("unreachable")
        }
    }
}
