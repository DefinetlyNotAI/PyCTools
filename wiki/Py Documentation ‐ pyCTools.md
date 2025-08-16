# PyCTools Library Documentation

## Overview

PyCTools is a high-performance Python library that provides native C-backed functionality for system-level operations that require maximum performance and direct hardware access. The library bridges Python's ease of use with C's raw performance through carefully designed wrapper classes that interface with compiled native code.

## Components

The library currently consists of two main modules:

1. **hwrng** - Hardware-based Random Number Generator that interfaces with CPU hardware to generate cryptographically secure random numbers at maximum performance. It utilizes the CPU's RDRAND instruction (where available) for true hardware randomness.

2. **processInspect** - Advanced process metrics collection system for detailed system and process monitoring with minimal overhead. Provides comprehensive performance data for Windows processes beyond standard Python libraries.

## Architecture

PyCTools employs a hybrid architecture:

- **Python Layer**: Clean, Pythonic wrapper classes providing a user-friendly API
- **Native Layer**: High-performance C/C++ code compiled to architecture-specific DLLs
- **Dynamic Loading**: Intelligent DLL loader that automatically selects the correct binary for the host architecture

The library uses a centralized DLL loading mechanism through the `_loadDLL` module, which implements sophisticated path resolution and error handling to ensure reliable operation across different environments.

## Key Strengths

- **Native Performance**: Direct access to hardware and system resources via compiled C/C++ code
- **Cross-Architecture Support**: Works seamlessly on both x86 and x64 Windows environments
- **Thread Safety**: Designed for concurrent operation in multithreaded environments
- **Comprehensive Metrics**: Detailed process and system statistics beyond what's available in standard Python libraries
- **Hardware RNG**: True random number generation using CPU hardware features
- **Minimal Overhead**: Engineered to add negligible performance impact while monitoring
- **Robust DLL Management**: Intelligent DLL discovery and loading with clear error reporting
- **Consistent API**: Uniform interface pattern across different modules for ease of use
- **Detailed Documentation**: Comprehensive documentation with examples and best practices

## Usage Domains

- Performance monitoring and diagnostics
- Security applications requiring cryptographically secure random numbers
- System administration and monitoring tools
- Performance-critical scientific or financial applications
- Resource usage tracking and optimization
- Application performance benchmarking

Each module is documented in detail in its dedicated documentation file.
