.PHONY: css css-watch

# Download Tailwind CLI + daisyUI for local dev (macOS ARM)
tools/tailwindcss:
	@mkdir -p tools
	curl -sLo tools/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
	chmod +x tools/tailwindcss
	curl -sLo app/static/css/daisyui.mjs https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.mjs
	curl -sLo app/static/css/daisyui-theme.mjs https://github.com/saadeghi/daisyui/releases/latest/download/daisyui-theme.mjs

# Build CSS once
css: tools/tailwindcss
	./tools/tailwindcss -i app/static/css/input.css -o app/static/css/main.css --minify

# Watch mode for development
css-watch: tools/tailwindcss
	./tools/tailwindcss -i app/static/css/input.css -o app/static/css/main.css --watch
