import Foundation

/// Private, machine-local identity aliases. This is deliberately a tiny JSON
/// lookup rather than a cloud contact database: calendar/Meet display names
/// win automatically, while known emails and Telegram handles can be joined
/// to the name the user actually recognizes.
enum PersonAliases {
    private struct File: Decodable { let people: [Person] }
    private struct Person: Decodable {
        let name: String
        let emails: [String]?
        let telegram: [String]?
    }

    static func resolve(identifiers: [String]) -> String? {
        let keys = Set(identifiers.map(normalize).filter { !$0.isEmpty })
        guard !keys.isEmpty,
              let data = try? Data(contentsOf: aliasesURL),
              let file = try? JSONDecoder().decode(File.self, from: data)
        else { return nil }

        for person in file.people {
            let aliases = (person.emails ?? []) + (person.telegram ?? [])
            if !keys.isDisjoint(with: aliases.map(normalize)) {
                let name = person.name.trimmingCharacters(in: .whitespacesAndNewlines)
                if !name.isEmpty { return name }
            }
        }
        return nil
    }

    private static var aliasesURL: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".config/meeting-copilot/people.json")
    }

    private static func normalize(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: "mailto:", with: "")
            .trimmingCharacters(in: CharacterSet(charactersIn: "@"))
    }
}
