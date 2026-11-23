import Foundation

struct Enroller: Sendable {
    static let nameLimit = 60
    private static let caLimit = 65_536
    private static let codeLimit = 8_192

    func payload(scanned raw: String) throws(NodeFailure) -> EnrollmentPayload {
        try NodeFailure.wrap { try parseEnrollment(raw: raw, now: Self.now) }
    }

    func payload(server serverInput: String, code codeInput: String) async throws(NodeFailure) -> EnrollmentPayload {
        let server = try NodeFailure.wrap { try normalizeServerInput(value: serverInput) }
        let code = try NodeFailure.wrap { try normalizeCode(value: codeInput) }
        guard let url = URL(string: server + "/api/android/enrollment-code") else { throw .rejected("enroll_file_invalid") }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: ["code": code])
        } catch {
            throw .invalidResponse
        }
        let (data, response) = try await firstContact(request)
        switch response.statusCode {
        case 200: break
        case 429: throw .rejected("rate_limited")
        case 403: throw .rejected("enroll_code_invalid")
        default: throw .rejected("enroll_unreachable")
        }
        guard data.count <= Self.codeLimit, let text = String(data: data, encoding: .utf8) else {
            throw .rejected("enroll_code_invalid")
        }
        let payload = try NodeFailure.wrap { try parseEnrollment(raw: text, now: Self.now) }
        guard payload.server == server else { throw .rejected("enroll_file_invalid") }
        return payload
    }

    func certificate(for payload: EnrollmentPayload) async throws(NodeFailure) -> (pem: String, fingerprint: String) {
        guard let url = URL(string: payload.server + "/nuxiva-ca.crt") else { throw .rejected("enroll_file_invalid") }
        let (data, response) = try await firstContact(URLRequest(url: url))
        guard response.statusCode == 200 else { throw .rejected("enroll_unreachable") }
        guard data.count <= Self.caLimit, let pem = String(data: data, encoding: .ascii) else {
            throw .rejected("enroll_ca_invalid")
        }
        let fingerprint = try NodeFailure.wrap { try caFingerprint(pem: pem) }
        guard pinMatches(expected: payload.pin, actual: fingerprint) else { throw .rejected("enroll_pin_mismatch") }
        return (pem, fingerprint)
    }

    func redeem(_ payload: EnrollmentPayload, displayName: String, model: String) async throws(NodeFailure) -> NodeProfile {
        let ca = try await certificate(for: payload)
        let identity = try NodeFailure.wrap { try DeviceIdentity.generate() }
        let nodeId = try NodeFailure.wrap { try newNodeId(model: model) }
        let trimmed = String(displayName.trimmingCharacters(in: .whitespacesAndNewlines).prefix(Self.nameLimit))
        let bootstrap = NodeProfile(
            nodeId: nodeId, name: trimmed.isEmpty ? nodeId : trimmed, server: payload.server,
            caPem: ca.pem, fingerprint: ca.fingerprint, seedHex: identity.seedHex(), token: "",
            peerId: payload.peer, enrolledAt: Date()
        )
        let body = [
            "token": payload.token, "id": nodeId, "name": bootstrap.name,
            "type": "ios", "pubkey": identity.publicHex(),
        ]
        let data: Data
        do {
            data = try await NodeClient(profile: bootstrap).post("/api/nodes/enroll", json: body)
        } catch .server(let code, _) {
            throw .rejected(code)
        } catch .pin {
            throw .rejected("enroll_pin_mismatch")
        } catch .rejected(let code) {
            throw .rejected(code)
        } catch {
            throw .rejected("enroll_unreachable")
        }
        let reply = try NodeClient.decode(EnrollReply.self, from: data)
        guard !reply.token.isEmpty else { throw .rejected("enroll_rejected") }
        var profile = bootstrap
        profile.token = reply.token
        if profile.peerId.isEmpty, let peer = reply.peer, peer.count == 64, peer.allSatisfy(\.isHexDigit) {
            profile.peerId = peer.lowercased()
        }
        return profile
    }

    private func firstContact(_ request: URLRequest) async throws(NodeFailure) -> (Data, HTTPURLResponse) {
        let session = URLSession(configuration: .node(timeout: 15), delegate: TLSDelegate(mode: .firstContact), delegateQueue: nil)
        defer { session.finishTasksAndInvalidate() }
        do {
            return try await NodeClient.send(request, session: session)
        } catch .pin {
            throw .rejected("enroll_unreachable")
        } catch {
            throw error
        }
    }

    private static var now: Int64 { Int64(Date().timeIntervalSince1970) }

    private struct EnrollReply: Decodable {
        let token: String
        let peer: String?
    }
}
