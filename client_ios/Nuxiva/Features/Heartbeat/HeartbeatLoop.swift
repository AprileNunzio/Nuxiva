import Foundation
import OSLog

enum LinkState: Equatable, Sendable {
    case connecting
    case online(Date)
    case offline(String)
    case revoked
    case securityAlert(String)
}

actor HeartbeatLoop {
    static let defaultInterval = 30
    private static let range = 10...300
    private let log = Logger(subsystem: "com.nuxiva.ios", category: "heartbeat")

    func beat(_ profile: NodeProfile, facts: DeviceFacts) async -> (LinkState, Int) {
        do {
            let client = try NodeClient(profile: profile, timeout: 15)
            let body = Data(heartbeatBody(facts: facts).utf8)
            let data = try await client.post("/api/nodes/heartbeat", body: body)
            let reply = try NodeClient.decode(Reply.self, from: data)
            let interval = min(max(reply.heartbeat ?? Self.defaultInterval, Self.range.lowerBound), Self.range.upperBound)
            return (.online(Date()), interval)
        } catch .unauthorized {
            return (.revoked, Self.defaultInterval)
        } catch .pin {
            return (.securityAlert("pin"), Self.defaultInterval)
        } catch {
            log.warning("Heartbeat failed for \(profile.nodeId, privacy: .public): \(error.code, privacy: .public)")
            return (.offline(error.code), Self.defaultInterval)
        }
    }

    private struct Reply: Decodable {
        let heartbeat: Int?
    }
}
