import AVFoundation
import UIKit

enum DeviceFactsReader {
    @MainActor
    static func read() -> DeviceFacts {
        let bytes = ProcessInfo.processInfo.physicalMemory
        return DeviceFacts(
            version: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "",
            hostname: UIDevice.current.model,
            microphone: AVAudioSession.sharedInstance().isInputAvailable,
            camera: AVCaptureDevice.default(for: .video) != nil,
            cpuCores: UInt32(clamping: ProcessInfo.processInfo.activeProcessorCount),
            ramMb: bytes / 1_048_576
        )
    }

    @MainActor
    static var model: String {
        UIDevice.current.model
    }
}
