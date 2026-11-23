import SwiftUI

@main
struct NuxivaApp: App {
    @State private var store = ProfileStore()

    var body: some Scene {
        WindowGroup {
            RootView(store: store)
        }
    }
}
