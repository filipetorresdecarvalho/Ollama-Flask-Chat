# Ollama-Flask-Chat: A Feature-Rich Web UI

This project is a complete, self-hosted web interface for interacting with local Ollama models. [cite_start]It evolved from a simple UI into a full-featured application with a multi-user architecture [cite: 5][cite_start], persistent chat history, and administrative controls, all built with Python and Flask.

It serves as a working example of what can be built with these tools and stands as a solid foundation for anyone interested in creating their own AI chat applications.

## Core Features

This is more than just a simple interface; it's a complete platform.

* **Full User & Session Management**: Users can sign up, log in, and manage their profiles.
* **Role-Based Permissions**: An admin panel allows the root user to assign roles (`admin`, `user`, `restricted`) to manage permissions.
* [cite_start]**Persistent, Private Conversations**: Each user has their own separate database for chat history [cite: 16, 17, 18, 19][cite_start], with the ability to manage multiple distinct conversations.
* [cite_start]**Dynamic Model Loading**: The application detects your locally installed Ollama models and allows you to switch between them from the UI.
* [cite_start]**Responsive Frontend**: The UI is designed to work on both desktop and mobile devices.
* **Robust Tooling**: The project includes scripts for easy first-time setup, production deployment, and diagnostics.

## Architectural Notes & Limitations

As a version 1.0 project, it has a few architectural characteristics worth noting. These were conscious design choices for this iteration and represent great opportunities for future improvements.

* **Synchronous HTTP Responses**: The interaction with Ollama is handled through standard HTTP requests. This means the AI's response will only appear after it has been fully generated, rather than streaming token-by-token. This can feel slow with larger models but is very reliable.
* **Command-Line Fallback**: For model discovery, the application first tries the `ollama` Python library. However, it is also designed to fall back to using the `ollama list` command directly in the shell if needed.
* **Known Issues**: There are some minor areas that could be polished, such as the Settings page being a placeholder. The project is provided as-is, representing a complete and functional state.

## Project Status & Future

I am incredibly proud of this project and how much it can do. It has been a fantastic learning experience. However, my journey with it has come to an end, as I am planning to build a completely new version from the ground up with a different architecture (likely focusing on real-time streaming and a more modern frontend framework).

Therefore, I will not be continuing active development on this repository.

The project is stable, functional, and complete according to its initial goals. I am publishing it in the hopes that it may help or inspire others.

Forks and pull requests are welcome! If you find a bug or wish to make an improvement, please feel free to do so. I will do my best to review and consider any community contributions. However, please do not expect me to add new features to this version myself.

Thank you for your interest, and I hope you enjoy the application!