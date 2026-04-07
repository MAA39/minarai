import SwiftUI

@main
struct MinaraiApp: App {
    var body: some Scene {
        MenuBarExtra("minarai", systemImage: "eye.circle") {
            MinaraiMenuView()
        }
        .menuBarExtraStyle(.window)

        Settings {
            Text("minarai Settings")
                .padding()
        }
    }
}

struct MinaraiMenuView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("minarai v0")
                .font(.headline)

            Text("Status: Not yet implemented")
                .font(.caption)
                .foregroundStyle(.secondary)

            Divider()

            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding()
        .frame(width: 240)
    }
}
