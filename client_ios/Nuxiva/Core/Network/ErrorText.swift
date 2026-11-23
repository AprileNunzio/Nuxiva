import SwiftUI

enum ErrorText {
    static let known: Set<String> = [
        "enroll_file_invalid", "enroll_file_expired", "enroll_code_invalid", "enroll_ca_invalid",
        "enroll_pin_mismatch", "enroll_unreachable", "enroll_rejected", "enroll_too_many_nodes",
        "enroll_node_exists", "enroll_invalid_node_id", "enroll_https_unavailable", "rate_limited",
        "unauthorized", "pin", "unreachable", "invalid_response", "storage_unavailable",
        "camera_unavailable", "node.error.clock", "node.error.signature", "node.error.replay",
        "node.error.scope_not_granted",
    ]

    static func key(_ code: String) -> LocalizedStringKey {
        LocalizedStringKey(name(code))
    }

    static func name(_ code: String) -> String {
        known.contains(code) ? "error.\(code)" : "error.generic"
    }
}
