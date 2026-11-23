import SwiftUI

struct EnrollmentView: View {
    @State var model: EnrollmentModel
    var onDone: (() -> Void)?

    var body: some View {
        Form {
            Section {
                TextField("enroll.name", text: $model.name)
                    .textContentType(.name)
                    .submitLabel(.done)
            } footer: {
                Text("enroll.name.hint")
            }
            if let failure = model.failure {
                Section {
                    Label(ErrorText.key(failure), systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(.red)
                }
            }
            content
        }
        .frame(maxWidth: 640)
        .frame(maxWidth: .infinity)
        .navigationTitle("enroll.title")
        .sheet(isPresented: scanning) {
            QRScannerSheet { raw in model.scanned(raw) } onFailure: { code in
                model.cancel()
                model.failure = code
            }
        }
        .onOpenURL { url in model.scanned(url.absoluteString) }
        .disabled(model.step == .working)
    }

    @ViewBuilder
    private var content: some View {
        switch model.step {
        case .choose, .scanning:
            Section {
                Button { model.step = .scanning } label: {
                    Label("enroll.scan", systemImage: "qrcode.viewfinder")
                }
                Button { model.step = .code } label: {
                    Label("enroll.code", systemImage: "number")
                }
            } footer: {
                Text("enroll.hint")
            }
        case .code:
            Section {
                TextField("enroll.server", text: $model.server)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                TextField("enroll.code.field", text: $model.code)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                Button("enroll.continue") { model.submitCode() }
                    .disabled(model.server.isEmpty || model.code.count < 6)
                Button("enroll.cancel", role: .cancel) { model.cancel() }
            } footer: {
                Text("enroll.code.hint")
            }
        case .confirm(let server, let fingerprint):
            Section {
                LabeledContent("enroll.server", value: server)
                Text(fingerprint)
                    .font(.system(.title2, design: .monospaced))
                    .frame(maxWidth: .infinity)
                    .accessibilityLabel(Text("enroll.fingerprint"))
                Button("enroll.fingerprint.match") { model.confirm() }
                Button("enroll.fingerprint.mismatch", role: .destructive) { model.cancel() }
            } header: {
                Text("enroll.fingerprint")
            } footer: {
                Text("enroll.fingerprint.hint")
            }
        case .working:
            Section {
                HStack(spacing: 12) {
                    ProgressView()
                    Text("enroll.working")
                }
            }
        }
    }

    private var scanning: Binding<Bool> {
        Binding(
            get: { model.step == .scanning },
            set: { visible in if !visible, model.step == .scanning { model.step = .choose } }
        )
    }
}
