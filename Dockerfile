FROM opencfd/openfoam-default:2312

RUN apt-get update && apt-get install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    curl \
    git \
    ca-certificates \
    python3-pip \
    python3-setuptools \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Etc/UTC

WORKDIR /root/app
COPY . /root/app

RUN python3 -m pip install -r requirements.txt

CMD ["bash", "-c", "python3 app/src/pipelines/of_pipeline.py -test"]
