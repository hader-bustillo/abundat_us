# syntax=docker/dockerfile:1
FROM 898314620182.dkr.ecr.us-east-2.amazonaws.com/ledeai_abundat_base:latest

WORKDIR /app

ENV FERNET_KEY PzMIbeKfyr-TExU-KeJsAhw8a8I-n8w6Szo2P3qB3-w=

RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

ENV TZ="America/New_York"

COPY environment.yml environment.yml

RUN export PATH="$HOME/miniconda/bin:$PATH" && \
    echo $PATH && \
    echo `which conda` && \
    conda update --all --yes && \
    conda env update -n root -f environment.yml && \
    conda list && \
    mkdir -p output && \
    mkdir -p logs

COPY . .

EXPOSE 5000

CMD [ "/root/miniconda/bin/python3", "-m" , "ai_article_handler"]