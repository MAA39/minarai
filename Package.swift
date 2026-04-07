// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "minarai",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "minarai", targets: ["minarai"])
    ],
    dependencies: [
        // MLX Swift for local VLM inference (future: direct Swift inference without vllm-mlx server)
        // .package(url: "https://github.com/ml-explore/mlx-swift-lm.git", from: "0.20.0"),
    ],
    targets: [
        .executableTarget(
            name: "minarai",
            dependencies: [],
            path: "Sources/minarai"
        )
    ]
)
