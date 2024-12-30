FROM selenium/standalone-chromium:latest

USER root

RUN apt-get update -y && apt-get install -y \
    git \
    python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# 创建虚拟环境
RUN python3 -m venv /app/venv

# 确保使用虚拟环境
ENV PATH="/app/venv/bin:$PATH"

# 升级 pip 并安装依赖
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs

# 确保权限正确
RUN chown -R seluser:seluser /app /app/venv

USER seluser

# 使用 shell 形式的 CMD，确保激活虚拟环境
CMD ["/bin/bash", "-c", "source /app/venv/bin/activate && exec scrapy crawl seek"]