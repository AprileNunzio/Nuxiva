import Foundation
import Observation
import OSLog

@MainActor
@Observable
final class ProfileStore {
    static let limit = 8

    private(set) var profiles: [NodeProfile] = []
    private(set) var loadFailure: String?
    private let keychain: Keychain
    private let log = Logger(subsystem: "com.nuxiva.ios", category: "profiles")

    init(keychain: Keychain = Keychain(service: "com.nuxiva.ios.node")) {
        self.keychain = keychain
        load()
    }

    func load() {
        do {
            let decoder = JSONDecoder()
            var loaded: [NodeProfile] = []
            for item in try keychain.all() {
                do {
                    loaded.append(try decoder.decode(NodeProfile.self, from: item))
                } catch {
                    log.error("Corrupt node profile skipped: \(String(describing: error), privacy: .public)")
                }
            }
            profiles = loaded.sorted { $0.enrolledAt < $1.enrolledAt }
            loadFailure = nil
        } catch {
            log.error("Keychain read failed: \(String(describing: error), privacy: .public)")
            loadFailure = "storage_unavailable"
        }
    }

    func add(_ profile: NodeProfile) throws(NodeFailure) {
        guard profiles.count < Self.limit, !profiles.contains(where: { $0.nodeId == profile.nodeId }) else {
            throw .rejected("enroll_too_many_nodes")
        }
        try persist(profile)
        profiles.append(profile)
    }

    func update(_ profile: NodeProfile) throws(NodeFailure) {
        guard let index = profiles.firstIndex(where: { $0.nodeId == profile.nodeId }) else { return }
        try persist(profile)
        profiles[index] = profile
    }

    func remove(_ nodeId: String) throws(NodeFailure) {
        do {
            try keychain.delete(account: nodeId)
        } catch {
            log.error("Keychain delete failed: \(String(describing: error), privacy: .public)")
            throw .rejected("storage_unavailable")
        }
        profiles.removeAll { $0.nodeId == nodeId }
    }

    private func persist(_ profile: NodeProfile) throws(NodeFailure) {
        do {
            try keychain.save(try JSONEncoder().encode(profile), account: profile.nodeId)
        } catch {
            log.error("Keychain write failed: \(String(describing: error), privacy: .public)")
            throw .rejected("storage_unavailable")
        }
    }
}
