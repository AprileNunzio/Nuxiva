import Foundation

enum NodeFailure: Error, Equatable, Sendable {
    case unreachable
    case pin
    case unauthorized
    case signatureRejected(String)
    case server(String, Int)
    case invalidResponse
    case rejected(String)

    var code: String {
        switch self {
        case .unreachable: "unreachable"
        case .pin: "pin"
        case .unauthorized: "unauthorized"
        case .signatureRejected(let detail): detail
        case .server(let detail, _): detail
        case .invalidResponse: "invalid_response"
        case .rejected(let detail): detail
        }
    }

    static func from(_ error: MobileError) -> NodeFailure {
        switch error {
        case .Rejected(let code): .rejected(code)
        }
    }

    static func wrap<T>(_ body: () throws -> T) throws(NodeFailure) -> T {
        do {
            return try body()
        } catch let error as MobileError {
            throw from(error)
        } catch {
            throw .invalidResponse
        }
    }

    static func from(_ error: URLError) -> NodeFailure {
        switch error.code {
        case .serverCertificateUntrusted, .serverCertificateHasBadDate, .serverCertificateNotYetValid,
             .serverCertificateHasUnknownRoot, .secureConnectionFailed, .clientCertificateRejected, .cancelled:
            .pin
        default:
            .unreachable
        }
    }
}
