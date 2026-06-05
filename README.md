## Technical Architecture & Dependencies

The desktop control unit is architected for ultra-low latency local processing, ensuring complete data privacy and offline operational capability.

- **Local Inference Engine:** Integrated with **LM Studio** via local OpenAI-compatible API endpoints for hosting and orchestrating quantized open-weight models.
- **Hardware Acceleration:** Fully optimized for Apple Silicon Unified Memory architectures (M-series Ultra execution).
- **Core Interface:** Python-based asynchronous runtime for handling cross-platform communication between the desktop host and external hardware modules.