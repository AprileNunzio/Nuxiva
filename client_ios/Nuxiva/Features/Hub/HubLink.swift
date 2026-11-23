import Foundation

enum HubLink {
    static func validated(_ relative: String) -> Bool {
        guard relative.hasPrefix("/screen/open?t=") else { return false }
        let token = relative.dropFirst("/screen/open?t=".count)
        return (16...128).contains(token.count)
            && token.unicodeScalars.allSatisfy { CharacterSet.alphanumerics.contains($0) && $0.isASCII || $0 == "_" || $0 == "-" }
    }

    static func open(_ profile: NodeProfile) async throws(NodeFailure) -> URL {
        let data = try await NodeClient(profile: profile).post("/api/nodes/display-link")
        let reply = try NodeClient.decode(Reply.self, from: data)
        guard validated(reply.path), let url = URL(string: profile.server + reply.path) else {
            throw .invalidResponse
        }
        return url
    }

    private struct Reply: Decodable {
        let path: String
    }
}
