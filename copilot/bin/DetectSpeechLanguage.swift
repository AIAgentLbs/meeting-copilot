import Foundation
import NaturalLanguage

// One UTF-8 transcript fragment on stdin; one tab-separated language/probability on stdout.
let input = String(data: FileHandle.standardInput.readDataToEndOfFile(), encoding: .utf8) ?? ""
let recognizer = NLLanguageRecognizer()
recognizer.processString(input)
let guesses = recognizer.languageHypotheses(withMaximum: 3)
if let top = guesses.max(by: { $0.value < $1.value }) {
    print("\(top.key.rawValue)\t\(top.value)")
} else {
    print("und\t0")
}
