import SwiftUI

struct HomeView: View {
    let store: ProfileStore
    @State private var hub: NodeProfile?
    @State private var enrolling = false
    @State private var failure: String?
    @State private var states: [String: LinkState] = [:]

    var body: some View {
        List {
            if let failure {
                Label(ErrorText.key(failure), systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
            }
            Section("home.servers") {
                ForEach(store.profiles) { profile in
                    row(profile)
                }
                .onDelete(perform: remove)
            }
        }
        .frame(maxWidth: 720)
        .frame(maxWidth: .infinity)
        .navigationTitle("home.title")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { enrolling = true } label: {
                    Label("home.add", systemImage: "plus")
                }
                .disabled(store.profiles.count >= ProfileStore.limit)
            }
        }
        .sheet(isPresented: $enrolling) {
            NavigationStack {
                EnrollmentView(model: EnrollmentModel(store: store))
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("enroll.cancel") { enrolling = false }
                        }
                    }
            }
            .onChange(of: store.profiles.count) { enrolling = false }
        }
        .fullScreenCover(item: $hub) { profile in
            HubView(profile: profile) { hub = nil }
        }
        .task { await refresh() }
        .refreshable { await refresh() }
    }

    private func row(_ profile: NodeProfile) -> some View {
        Button { hub = profile } label: {
            HStack(spacing: 12) {
                Image(systemName: "rectangle.on.rectangle")
                    .font(.title2)
                    .foregroundStyle(.tint)
                VStack(alignment: .leading, spacing: 4) {
                    Text(profile.name).font(.headline)
                    Text(profile.server).font(.caption).foregroundStyle(.secondary)
                    Text(statusKey(states[profile.nodeId])).font(.caption2).foregroundStyle(.secondary)
                }
                Spacer()
                Text("home.open").font(.callout.weight(.semibold))
            }
        }
        .accessibilityHint(Text("home.open.hint"))
    }

    private func statusKey(_ state: LinkState?) -> LocalizedStringKey {
        switch state {
        case .none, .connecting: "status.connecting"
        case .online: "status.online"
        case .offline: "status.offline"
        case .revoked: "status.revoked"
        case .securityAlert: "status.security"
        }
    }

    private func refresh() async {
        let facts = DeviceFactsReader.read()
        let loop = HeartbeatLoop()
        for profile in store.profiles {
            let (state, _) = await loop.beat(profile, facts: facts)
            states[profile.nodeId] = state
        }
    }

    private func remove(at offsets: IndexSet) {
        for profile in offsets.map({ store.profiles[$0] }) {
            do {
                try store.remove(profile.nodeId)
                failure = nil
            } catch {
                failure = error.code
            }
        }
    }
}
