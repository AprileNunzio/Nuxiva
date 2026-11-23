import Foundation
import Security

enum PinnedTrust {
    static func certificate(pem: String) throws(NodeFailure) -> SecCertificate {
        let der = try NodeFailure.wrap { try caDer(pem: pem) }
        guard let certificate = SecCertificateCreateWithData(nil, der as CFData) else {
            throw NodeFailure.rejected("enroll_ca_invalid")
        }
        return certificate
    }

    static func evaluate(_ trust: SecTrust, anchor: SecCertificate) -> Bool {
        guard SecTrustSetPolicies(trust, SecPolicyCreateBasicX509()) == errSecSuccess,
              SecTrustSetAnchorCertificates(trust, [anchor] as CFArray) == errSecSuccess,
              SecTrustSetAnchorCertificatesOnly(trust, true) == errSecSuccess else {
            return false
        }
        var error: CFError?
        return SecTrustEvaluateWithError(trust, &error)
    }

    static func short(_ fingerprint: String) -> String {
        let head = Array(fingerprint.uppercased().prefix(16))
        return stride(from: 0, to: head.count, by: 4)
            .map { String(head[$0..<min($0 + 4, head.count)]) }
            .joined(separator: "-")
    }
}

final class TLSDelegate: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    enum Mode {
        case firstContact
        case pinned(SecCertificate)
    }

    private let mode: Mode

    init(mode: Mode) {
        self.mode = mode
    }

    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge
    ) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
        decide(challenge)
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didReceive challenge: URLAuthenticationChallenge
    ) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
        decide(challenge)
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest
    ) async -> URLRequest? {
        nil
    }

    func decide(_ challenge: URLAuthenticationChallenge) -> (URLSession.AuthChallengeDisposition, URLCredential?) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust else {
            return (.performDefaultHandling, nil)
        }
        switch mode {
        case .firstContact:
            return (.useCredential, URLCredential(trust: trust))
        case .pinned(let anchor):
            return PinnedTrust.evaluate(trust, anchor: anchor)
                ? (.useCredential, URLCredential(trust: trust))
                : (.cancelAuthenticationChallenge, nil)
        }
    }
}

extension URLSessionConfiguration {
    static func node(timeout: TimeInterval) -> URLSessionConfiguration {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.tlsMinimumSupportedProtocolVersion = .TLSv12
        configuration.timeoutIntervalForRequest = timeout
        configuration.timeoutIntervalForResource = timeout * 2
        configuration.httpCookieAcceptPolicy = .never
        configuration.httpShouldSetCookies = false
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        configuration.waitsForConnectivity = false
        return configuration
    }
}
