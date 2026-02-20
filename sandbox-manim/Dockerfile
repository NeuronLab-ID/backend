# Manim Animation Sandbox
# Uses official ManimCE image with additional LaTeX packages
FROM manimcommunity/manim:stable

# Install additional LaTeX packages for math formulas
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-extra \
    texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*

# Copy runner script
COPY manim_runner.py /app/manim_runner.py
WORKDIR /app

# Run as manimuser (default in manimcommunity image)
USER manimuser

# Environment
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["python", "manim_runner.py"]
