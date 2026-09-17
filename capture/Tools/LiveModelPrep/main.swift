import FluidAudio
import Foundation

@main
struct LiveModelPrep {
    static func main() async throws {
        let language = CommandLine.arguments.dropFirst().first ?? "ru-RU"
        let root = FileManager.default.urls(
            for: .applicationSupportDirectory, in: .userDomainMask
        ).first!
            .appendingPathComponent("FluidAudio", isDirectory: true)
            .appendingPathComponent("Models", isDirectory: true)
        let destination = root
            .appendingPathComponent(Repo.nemotronMultilingual.folderName, isDirectory: true)
            .appendingPathComponent(
                StreamingNemotronMultilingualAsrManager.languageDirectory(for: language),
                isDirectory: true
            )
            .appendingPathComponent("1120ms", isDirectory: true)

        print("Preparing MeetingCopilot live model for \(language)…")
        _ = try await StreamingNemotronMultilingualAsrManager.downloadVariant(
            languageCode: language,
            chunkMs: 1120,
            to: root
        ) { update in
            let percent = Int(update.fractionCompleted * 100)
            if percent % 10 == 0 { print("\(percent)%") }
        }
        guard FileManager.default.fileExists(
            atPath: destination.appendingPathComponent("metadata.json").path
        ) else {
            throw NSError(
                domain: "MeetingCopilotLiveModel",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "model download did not finish"]
            )
        }
        print("MeetingCopilot live model ready: \(destination.path)")
    }
}
