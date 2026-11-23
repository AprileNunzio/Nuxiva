import SwiftUI

struct HubView: View {
    let profile: NodeProfile
    let onClose: () -> Void

    @State private var phase: Phase = .connecting
    @Environment(\.scenePhase) private var scenePhase

    enum Phase {
        case connecting
        case showing(URL, SecCertificate)
        case failed(String)
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            switch phase {
            case .connecting:
                ProgressView("hub.connecting")
                    .tint(.white)
                    .foregroundStyle(.white)
            case .showing(let url, let anchor):
                HubWebView(url: url, anchor: anchor) { code in phase = .failed(code) }
                    .ignoresSafeArea()
            case .failed(let code):
                failure(code)
            }
        }
        .overlay(alignment: .topTrailing) {
            Button(action: onClose) {
                Image(systemName: "xmark.circle.fill")
                    .font(.title)
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(.white.opacity(0.6))
                    .padding()
            }
            .accessibilityLabel(Text("hub.close"))
        }
        .statusBarHidden()
        .persistentSystemOverlays(.hidden)
        .task { await connect() }
        .onAppear { UIApplication.shared.isIdleTimerDisabled = true }
        .onDisappear { UIApplication.shared.isIdleTimerDisabled = false }
        .onChange(of: scenePhase) { _, next in
            if next == .active, case .failed = phase { Task { await connect() } }
        }
    }

    private func failure(_ code: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.exclamationmark")
                .font(.largeTitle)
            Text(ErrorText.key(code))
                .multilineTextAlignment(.center)
            Button("hub.retry") { Task { await connect() } }
                .buttonStyle(.borderedProminent)
        }
        .foregroundStyle(.white)
        .padding(32)
        .frame(maxWidth: 520)
    }

    private func connect() async {
        phase = .connecting
        let facts = DeviceFactsReader.read()
        let (state, _) = await HeartbeatLoop().beat(profile, facts: facts)
        switch state {
        case .revoked:
            phase = .failed("unauthorized")
            return
        case .securityAlert(let code):
            phase = .failed(code)
            return
        default:
            break
        }
        do {
            let anchor = try PinnedTrust.certificate(pem: profile.caPem)
            let url = try await HubLink.open(profile)
            phase = .showing(url, anchor)
        } catch {
            phase = .failed(error.code)
        }
    }
}
