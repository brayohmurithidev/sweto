#!/usr/bin/env bash

set -euo pipefail

flutter run -d 'iPhone 17 Pro' \
  --dart-define=APP_ENV=local \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000