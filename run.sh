#!/usr/bin/env bash
source /group_shares/fnl/bulk/code/internal/GUIs/ImageSearcher_dev/venv/bin/activate
python /group_shares/fnl/bulk/code/internal/GUIs/ImageSearcher_dev/manage.py runserver 8080 &
chromium-browser http://127.0.0.1:8080/dicoms/
