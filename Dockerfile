# ===================================================================
# Dockerfile for Event-Driven Quant Agent Lab
#
# Base: Ubuntu 22.04 + CUDA 12.5.1 + CUDNN + Miniconda CPython 3.10
# Features:
# - Installs this project in editable mode with dev dependencies
# - Includes git and SSH client/server for GitHub-based updates
# - Starts SSH server automatically
# - Full UTF-8 locale support
# ===================================================================

FROM nvidia/cuda:12.5.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV CONDA_DIR=/opt/miniconda3
ENV PATH=$CONDA_DIR/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Use Ubuntu 22.04 (jammy) mirrors and keep the security pocket official.
RUN echo "deb https://mirrors.ustc.edu.cn/ubuntu/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        locales \
        openssh-client \
        openssh-server \
        pkg-config \
        unzip \
        wget \
    && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# SSH service configuration. Bind the container port to localhost when running.
RUN mkdir -p /var/run/sshd /root/.ssh && \
    chmod 700 /root/.ssh && \
    echo 'root:yourpwd' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
EXPOSE 22

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p $CONDA_DIR && \
    rm /tmp/miniconda.sh && \
    conda init bash

RUN conda update conda -y && \
    conda config --set ssl_verify true && \
    conda config --set show_channel_urls yes && \
    conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/ && \
    conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/main/ && \
    conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/free/ && \
    conda create -n quant python=3.10 cpython -y && \
    conda clean -ay

SHELL ["conda", "run", "-n", "quant", "/bin/bash", "-c"]

WORKDIR /workspace/event-driven-quant-agent-lab

COPY pyproject.toml README.md upstreams-manifest.json ./
COPY docs ./docs
COPY src ./src
COPY tests ./tests

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"

RUN echo '#!/bin/bash' > /start.sh && \
    echo 'set -e' >> /start.sh && \
    echo 'source /opt/miniconda3/etc/profile.d/conda.sh' >> /start.sh && \
    echo 'conda activate quant' >> /start.sh && \
    echo 'service ssh start' >> /start.sh && \
    echo 'echo "SSH server started. quant environment activated."' >> /start.sh && \
    echo 'exec /bin/bash' >> /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD conda run -n quant python -c "import quant_agent_lab" || exit 1

LABEL maintainer="yearn@local.gpu" \
      version="1.0" \
      description="Event-Driven Quant Agent Lab dev environment - Ubuntu 22.04 + CUDA 12.5.1 + Miniconda Python 3.10 + SSH + Git"
