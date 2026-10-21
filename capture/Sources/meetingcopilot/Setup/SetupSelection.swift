import Foundation

/// A no-cost authentication check for the two summary API providers. Both
/// official APIs expose an authenticated model-list endpoint, so setup can
/// verify a key without generating (and billing for) any text.
enum SummaryKeyProbe {
    enum Provider {
        case anthropic
        case openAI
    }

    static func request(provider: Provider, key: String) -> URLRequest {
        let url: URL
        switch provider {
        case .anthropic:
            url = URL(string: "https://api.anthropic.com/v1/models?limit=1")!
        case .openAI:
            url = URL(string: "https://api.openai.com/v1/models")!
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 15
        switch provider {
        case .anthropic:
            request.setValue(key, forHTTPHeaderField: "x-api-key")
            request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        case .openAI:
            request.setValue("Bearer \(key)", forHTTPHeaderField: "authorization")
        }
        return request
    }

    static func works(provider: Provider, key: String) async -> Bool {
        guard let (_, response) = try? await URLSession.shared.data(
            for: request(provider: provider, key: key)
        ) else { return false }
        return (response as? HTTPURLResponse)?.statusCode == 200
    }
}
