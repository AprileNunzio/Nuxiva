import SwiftUI

struct RootView: View {
    let store: ProfileStore

    var body: some View {
        NavigationStack {
            if store.profiles.isEmpty {
                EnrollmentView(model: EnrollmentModel(store: store))
            } else {
                HomeView(store: store)
            }
        }
        .tint(.cyan)
        .overlay(alignment: .bottom) {
            if let failure = store.loadFailure {
                Label(ErrorText.key(failure), systemImage: "lock.trianglebadge.exclamationmark")
                    .padding()
                    .background(.regularMaterial, in: Capsule())
                    .padding()
            }
        }
    }
}
