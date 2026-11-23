import Foundation
import Testing
@testable import Nuxiva

struct CoreBindingTests {
    private struct Contract: Decodable {
        struct Case: Decodable {
            struct Payload: Decodable {
                let token: String
                let pin: String
                let expires: Int64
            }
            let name: String
            let link: String
            let payload: Payload
        }
        let now: Int64
        let cases: [Case]
    }

    private func contract() throws -> Contract {
        let bundle = Bundle(for: BundleToken.self)
        let url = try #require(bundle.url(forResource: "android_enrollment", withExtension: "json"))
        return try JSONDecoder().decode(Contract.self, from: Data(contentsOf: url))
    }

    @Test func contractLinksParseInSwift() throws {
        let contract = try contract()
        for item in contract.cases {
            let parsed = try Enroller().payload(scanned: item.link)
            #expect(parsed.token == item.payload.token)
            #expect(parsed.pin == item.payload.pin)
            #expect(parsed.expires == item.payload.expires)
        }
    }

    @Test func invalidLinkMapsToALocalisedError() {
        #expect(throws: NodeFailure.rejected("enroll_file_invalid")) {
            try Enroller().payload(scanned: "nuxiva://enroll?d=%%%")
        }
        #expect(ErrorText.name("enroll_file_invalid") == "error.enroll_file_invalid")
        #expect(ErrorText.name("something_new") == "error.generic")
    }

    @Test func signaturesAreProducedForTheServerFormat() throws {
        let identity = try DeviceIdentity.generate()
        let restored = try DeviceIdentity.fromSeedHex(seed: identity.seedHex())
        #expect(restored.publicHex() == identity.publicHex())
        let signed = try restored.sign(node: "ios-iphone-abcdef", method: "POST", path: "/api/nodes/heartbeat", body: Data("{}".utf8), now: 1_760_000_000)
        #expect(signed.signature.count == 128)
        #expect(signed.nonce.count == 32)
    }

    @Test func hubLinksAreValidatedStrictly() {
        #expect(HubLink.validated("/screen/open?t=abcdefghijklmnop_-12"))
        #expect(!HubLink.validated("/screen/open?t=short"))
        #expect(!HubLink.validated("https://evil.example/screen/open?t=abcdefghijklmnop"))
        #expect(!HubLink.validated("/screen/open?t=abcdefghijklmnop&x=1"))
    }

    @Test func fingerprintsAreShortenedForHumans() {
        #expect(PinnedTrust.short("0b7a27cf25a4d69099a057af63164a42") == "0B7A-27CF-25A4-D690")
    }

    @Test func heartbeatDeclaresTheIosAgent() throws {
        let facts = DeviceFacts(version: "1", hostname: "iPad", microphone: false, camera: true, cpuCores: 6, ramMb: 4096)
        let body = try #require(try JSONSerialization.jsonObject(with: Data(heartbeatBody(facts: facts).utf8)) as? [String: Any])
        #expect(body["agent"] as? String == "ios")
    }
}

private final class BundleToken {}
