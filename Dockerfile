FROM selenium/standalone-chromium:latest

USER root

# 安装 git 和 python3.12-venv
RUN apt-get update -y && apt-get install -y \
    git \
    python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 克隆项目
RUN git clone https://github.com/qinscode/SeekSpider.git .

# 复制修改后的 requirements.txt
COPY requirements.txt .

# 创建并激活虚拟环境
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# 升级 pip 并安装依赖
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs
RUN chown -R seluser:seluser /app /app/venv

USER seluser

CMD ["scrapy", "crawl", "seek"]