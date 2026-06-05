#!/bin/bash -e

uv run ruff check task_orchestrator tests --fix

uv run pyright task_orchestrator tests
