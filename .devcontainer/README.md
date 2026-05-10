# pi Development Container

A Docker-based development environment for the pi monorepo using bash.

## Quick Start

### VS Code Dev Container

Open the project in VS Code and press `F1` → "Dev Containers: Reopen in Container"

### Docker Compose (Standalone)

```bash
cd .devcontainer
docker-compose up -d
docker-compose exec pi-dev bash
```

### Docker Run (Manual)

```bash
docker build -t pi-dev .
docker run -it --rm \
  -v $(pwd):/workspace \
  -p 3000:3000 \
  -p 8080:8080 \
  -w /workspace \
  pi-dev bash
```

## What's Included

- Node.js 22 (LTS)
- npm with workspace support
- System deps: Cairo, Pango, JPEG, GIF, SVG, ripgrep, fd-find
- tmux, zsh, fish
- tsx, TypeScript, Biome globally available

## Post-Setup

After entering the container:

```bash
npm install    # if not already done
npm run build  # build all packages
npm run check  # lint and typecheck
npm test       # run tests
```

## Notes

- Runs as `node` user (not root)
- `HUSKY=0` disables git hooks in container
- SSH agent and gitconfig forwarded from host