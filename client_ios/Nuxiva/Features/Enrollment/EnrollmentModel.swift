import Foundation
import Observation

@MainActor
@Observable
final class EnrollmentModel {
    enum Step: Equatable {
        case choose
        case scanning
        case code
        case confirm(String)
        case working
    }

    var step: Step = .choose
    var server = ""
    var code = ""
    var name = ""
    var failure: String?

    private var pending: EnrollmentPayload?
    private let enroller = Enroller()
    private let store: ProfileStore

    init(store: ProfileStore) {
        self.store = store
    }

    func scanned(_ raw: String) {
        do {
            let payload = try enroller.payload(scanned: raw)
            pending = payload
            Task { await finish(payload) }
        } catch {
            fail(error.code)
        }
    }

    func submitCode() {
        step = .working
        failure = nil
        Task {
            do {
                let payload = try await enroller.payload(server: server, code: code)
                let ca = try await enroller.certificate(for: payload)
                pending = payload
                step = .confirm(PinnedTrust.short(ca.fingerprint))
            } catch {
                fail(error.code)
            }
        }
    }

    func confirm() {
        guard let payload = pending else {
            step = .choose
            return
        }
        Task { await finish(payload) }
    }

    func cancel() {
        pending = nil
        failure = nil
        step = .choose
    }

    private func finish(_ payload: EnrollmentPayload) async {
        step = .working
        failure = nil
        do {
            let profile = try await enroller.redeem(payload, displayName: name, model: DeviceFactsReader.model)
            try store.add(profile)
            pending = nil
            step = .choose
        } catch {
            fail(error.code)
        }
    }

    private func fail(_ code: String) {
        pending = nil
        failure = code
        step = .choose
    }
}
