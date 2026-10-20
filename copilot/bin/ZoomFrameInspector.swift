import AppKit
import Foundation
import Vision

struct Observation: Codable {
    let text: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
    let confidence: Float
}

guard CommandLine.arguments.count == 2,
      let image = NSImage(contentsOfFile: CommandLine.arguments[1]),
      let data = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: data),
      let cgImage = bitmap.cgImage
else {
    FileHandle.standardError.write(Data("usage: ZoomFrameInspector IMAGE\n".utf8))
    exit(2)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["ru-RU", "en-US"]
request.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: cgImage).perform([request])

let observations = (request.results ?? []).compactMap { item -> Observation? in
    guard let candidate = item.topCandidates(1).first else { return nil }
    let box = item.boundingBox
    return Observation(
        text: candidate.string,
        x: box.origin.x,
        y: box.origin.y,
        width: box.width,
        height: box.height,
        confidence: candidate.confidence
    )
}.sorted {
    if abs($0.y - $1.y) > 0.01 { return $0.y > $1.y }
    return $0.x < $1.x
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
FileHandle.standardOutput.write(try encoder.encode(observations))
FileHandle.standardOutput.write(Data("\n".utf8))
