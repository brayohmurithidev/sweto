#!/usr/bin/env bash

set -euo pipefail

flutter run -d 23129RAA4G \
  --dart-define=APP_ENV=local \
  --dart-define=API_BASE_URL=http://192.168.8.8:8000