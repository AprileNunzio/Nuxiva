import Foundation
import Security

enum KeychainFailure: Error, Equatable, Sendable {
    case status(OSStatus)
    case corrupt
}

struct Keychain: Sendable {
    let service: String

    private func base(account: String? = nil) -> [String: Any] {
        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecUseDataProtectionKeychain as String: true,
        ]
        if let account {
            query[kSecAttrAccount as String] = account
        }
        return query
    }

    func save(_ data: Data, account: String) throws(KeychainFailure) {
        try delete(account: account)
        var item = base(account: account)
        item[kSecValueData as String] = data
        item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        item[kSecAttrSynchronizable as String] = false
        let status = SecItemAdd(item as CFDictionary, nil)
        guard status == errSecSuccess else { throw .status(status) }
    }

    func delete(account: String) throws(KeychainFailure) {
        let status = SecItemDelete(base(account: account) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw .status(status) }
    }

    func deleteAll() throws(KeychainFailure) {
        let status = SecItemDelete(base() as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw .status(status) }
    }

    func all() throws(KeychainFailure) -> [Data] {
        var query = base()
        query[kSecMatchLimit as String] = kSecMatchLimitAll
        query[kSecReturnData as String] = true
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return [] }
        guard status == errSecSuccess else { throw .status(status) }
        guard let items = result as? [Data] else { throw .corrupt }
        return items
    }
}
