FROM archlinux:base

# System Level Prereq's
RUN pacman -Syy
RUN pacman -S gcc git python python-pip --noconfirm

# Setup non-root user for development
RUN useradd --create-home --user-group --home-dir /home/dev --uid 1001 dev
USER dev
WORKDIR /home/dev

# Setup Octoprint dev environment
RUN git clone https://github.com/OctoPrint/OctoPrint ./octoprint
WORKDIR /home/dev/octoprint
RUN python -m venv venv
RUN venv/bin/pip install --upgrade pip
RUN venv/bin/pip install -e .[develop,plugins]
RUN mkdir -p /home/dev/.octoprint/plugins
ENV PATH="/home/dev/.local/bin:/home/dev/octoprint/venv/bin:${PATH}"
RUN venv/bin/pip install "https://github.com/jneilliii/OctoPrint-PlotlyTempGraph/archive/master.zip"

# Done
ENTRYPOINT "octoprint serve"
