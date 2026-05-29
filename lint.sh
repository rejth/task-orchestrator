#!/bin/bash -e

uv run ruff check src tests --fix

uv run pyright src tests
