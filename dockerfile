# 베이스 이미지 사용
FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

ARG SSH_ROOT_PASSWORD=${SSH_ROOT_PASSWORD:-root}
ARG SSH_USER=${SSH_USER:-ubuntu}
ARG SSH_PASSWORD=${SSH_PASSWORD:-ubuntu}

ENV SSH_ROOT_PASSWORD=${SSH_ROOT_PASSWORD}
ENV SSH_USER=${SSH_USER}
ENV SSH_PASSWORD=${SSH_PASSWORD}

ENV TZ=Asia/Seoul

RUN echo $TZ > /etc/timezone
RUN sed -i "s#/archive.ubuntu.com/#/mirror.kakao.com/#g" \
            /etc/apt/sources.list

RUN sed -i 's/archive.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list && \
    apt-get update -qq && \
    apt-get install -qq -y \
      apt-utils \    
      aptitude \
      curl \
      dnsutils \
      iputils-ping \
      net-tools \
      netcat \
      openssh-server \
      ssh \
      sudo \
      telnet \
      traceroute \
      vim && \
    apt-get clean -qq autoclean && \
    apt-get autoremove -qq --yes && \
    rm -rf /var/lib/apt/lists /var/lib/dpkg/info /tmp/* /var/tmp/*

RUN echo "root:$SSH_ROOT_PASSWORD" | chpasswd && \
    cp -rf /etc/skel/.bash* /root/. && \
    echo 'export PS1="\[\033[01;32m\]\u\[\e[m\]\[\033[01;32m\]@\[\e[m\]\[\033[01;32m\]\h\[\e[m\]:\[\033[01;34m\]\W\[\e[m\]$ "' >> ~/.bashrc && \
    ssh-keygen -A

RUN useradd -c "$SSH_USER" -m -d /home/$SSH_USER -s /bin/bash $SSH_USER && \
    usermod -aG sudo $SSH_USER && \
    echo "$SSH_USER:$SSH_PASSWORD" | chpasswd && \
    echo 'export PS1="\[\e[33m\]\u\[\e[m\]\[\e[37m\]@\[\e[m\]\[\e[34m\]\h\[\e[m\]:\[\033[01;31m\]\W\[\e[m\]$ "' >> /home/$SSH_USER/.bashrc && \
    echo "$SSH_USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# SSH Configure Settings
RUN mkdir /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/g' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/g' /etc/ssh/sshd_config && \
    sed -i 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config

# Expose SSH port
EXPOSE 22

# Start SSH server
CMD ["/usr/sbin/sshd", "-D"]