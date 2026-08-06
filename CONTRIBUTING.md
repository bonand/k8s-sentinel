# Contributing to K8s Sentinel

Thank you for your interest in contributing to K8s Sentinel! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for local testing)
- A Kubernetes cluster (optional, for integration tests)

### Installation

```bash
git clone https://github.com/your-org/k8s-sentinel.git
cd k8s-sentinel

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make dev
