import Foundation

struct NodeClient: Sendable {
    static let responseLimit = 2 << 20

    private let profile: NodeProfile
    private let anchor: TLSDelegate
    private let timeout: TimeInterval

    init(profile: NodeProfile, timeout: TimeInterval = 30) throws(NodeFailure) {
        self.profile = profile
        self.anchor = TLSDelegate(mode: .pinned(try PinnedTrust.certificate(pem: profile.caPem)))
        self.timeout = timeout
    }

    func post(_ path: String, json: [String: String] = [:]) async throws(NodeFailure) -> Data {
        let body: Data
        do {
            body = try JSONSerialization.data(withJSONObject: json, options: [.sortedKeys])
        } catch {
            throw .invalidResponse
        }
        return try await post(path, body: body)
    }

    func post(_ path: String, body: Data) async throws(NodeFailure) -> Data {
        guard let url = URL(string: profile.server + path) else { throw .rejected("enroll_file_invalid") }
        let signed = try NodeFailure.wrap {
            try DeviceIdentity.fromSeedHex(seed: profile.seedHex)
                .sign(node: profile.nodeId, method: "POST", path: path, body: body, now: Int64(Date().timeIntervalSince1970))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(signed.node, forHTTPHeaderField: "X-Nuxiva-Node")
        request.setValue(String(signed.ts), forHTTPHeaderField: "X-Nuxiva-Ts")
        request.setValue(signed.nonce, forHTTPHeaderField: "X-Nuxiva-Nonce")
        request.setValue(signed.signature, forHTTPHeaderField: "X-Nuxiva-Sig")
        if !profile.token.isEmpty {
            request.setValue("Bearer \(profile.token)", forHTTPHeaderField: "Authorization")
        }
        let session = URLSession(configuration: .node(timeout: timeout), delegate: anchor, delegateQueue: nil)
        defer { session.finishTasksAndInvalidate() }
        let (data, response) = try await NodeClient.send(request, session: session)
        return try NodeClient.check(data, response)
    }

    static func send(_ request: URLRequest, session: URLSession) async throws(NodeFailure) -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw NodeFailure.invalidResponse }
            guard data.count <= responseLimit else { throw NodeFailure.server("response_too_large", http.statusCode) }
            return (data, http)
        } catch let failure as NodeFailure {
            throw failure
        } catch let error as URLError {
            throw NodeFailure.from(error)
        } catch {
            throw NodeFailure.unreachable
        }
    }

    static func check(_ data: Data, _ response: HTTPURLResponse) throws(NodeFailure) -> Data {
        let detail = (try? JSONDecoder().decode(Detail.self, from: data))?.detail ?? ""
        switch response.statusCode {
        case 200..<300:
            return data
        case 401:
            if detail.hasPrefix("node.error.") { throw .signatureRejected(detail) }
            throw .unauthorized
        default:
            throw .server(detail.isEmpty ? "http_\(response.statusCode)" : detail, response.statusCode)
        }
    }

    static func decode<T: Decodable>(_ type: T.Type, from data: Data) throws(NodeFailure) -> T {
        do {
            return try JSONDecoder().decode(type, from: data)
        } catch {
            throw .invalidResponse
        }
    }

    private struct Detail: Decodable {
        let detail: String
    }
}
