import Foundation

struct NodeProfile: Codable, Equatable, Identifiable, Sendable {
    let nodeId: String
    var name: String
    var server: String
    let caPem: String
    let fingerprint: String
    let seedHex: String
    var token: String
    var peerId: String
    let enrolledAt: Date

    var id: String { nodeId }

    var serverURL: URL? { URL(string: server) }
}
