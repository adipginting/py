FROM mcr.microsoft.com/devcontainers/javascript-node:22-bookworm

# Install system dependencies required for pi
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    fd-find \
    ripgrep \
    git \
    curl \
    ca-certificates \
    tmux \
    zsh \
    fish \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for fdfind as fd (common alias)
RUN ln -s $(which fdfind) /usr/local/bin/fd

# Set up workspace directory
WORKDIR /workspace

# Set up workspace directory
WORKDIR /workspace

# Ensure the node user owns the workspace
RUN chown -R node:node /workspace

# Switch to node user
USER node

# Install common global npm packages
RUN npm install -g tsx typescript @biomejs/biome concurrently

# Set up shell environment
RUN echo 'export PATH="$HOME/.localnode/bin:$PATH"' >> ~/.bashrc
RUN echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
RUN echo 'eval "$(register-python-argcomplete pip)"' >> ~/.bashrc

# Create some useful aliases
RUN echo 'alias ll="ls -la"' >> ~/.bashrc
RUN echo 'alias gs="git status"' >> ~/.bashrc
RUN echo 'alias gp="git pull"' >> ~/.bashrc

# Set default shell to bash
ENV SHELL=/bin/bash

# Keep container running for development
CMD ["/bin/bash"]