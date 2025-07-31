# 🐳 Docker Log Streamer & Partitioner

[![Python](https://img.shields.io/badge/python-3.7%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/redis-used-red?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/docker-compatible-2496ed?logo=docker&logoColor=white)](https://www.docker.com/)

---

> **⏱ Robust, automatic, gzipped, and partitioned streaming of logs from multiple Docker containers.  
> Handles container restarts, deletions, and lets you archive logs reliably!**

---

## ✨ Features

- **Real-Time Streaming:** Instantly tails log output from any number of Docker containers.
- **Partitioned & Compressed:** Splits logs into `.log.gz` files by size.
- **Auto Timestamp & Naming:** Filenames include name, partition, and UTC timestamp.
- **Resilient:** Recovers if containers are restarted/pruned—even if Docker container ID changes!
- **Partition Index via Redis:** Never lose your partition number.
- **Multi-Container:** Tails multiple containers in parallel.
- **YAML Config:** Add containers to monitor in one config file.

---

## 🖼️ How It Works

<details>
<summary><b>(Click to expand) See container-to-file diagram</b></summary>

```mermaid
flowchart LR
  subgraph Docker_Containers
    A[my_app]
    B[db]
  end
  A -->|writes logs| L1[/container id1 log/]
  B -->|writes logs| L2[/container id2 log/]
  L1 & L2 -->|monitored by| S[Log Streamer Script]
  S -->|creates| F1[[output/my_app-01-<timestamp>.log.gz]]
  S -->|creates| F2[[output/db-01-<timestamp>.log.gz]]
  S -.->|stores index| R[(Redis)]
</details>

*If diagram does not render, [see GitHub’s Mermaid diagram support](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams#creating-mermaid-diagrams).*

---

## 🛠️ Setup & Usage

### 1. **Install prerequisites**

shell
pip install pyyaml redis
_Docker and Redis servers must also be running._

---

### 2. **Configure containers to stream**

Create a `config.yaml` like:

yaml
containers:
  - my_app
  - db

---

### 3. **Run it!**

shell
python log_streamer.py

---

### 📂 **You’ll Get:**


./output/
  my_app-01-20240717123000.log.gz
  my_app-02-20240717123500.log.gz
  db-01-20240717123100.log.gz

---

## 💡 Why Partition & Compress?

- **Easy archiving:** Chunked logs are manageable.
- **Disk space:** Single compressed files keep size tiny.
- **Crash/restart-safe:** Never lose or corrupt logs due to container churn.
- **Disaster recovery:** Logs continue regardless of Docker ID changes.

---

## ⚡ Advanced Options

- **Customize folders:** Change `DOCKER_LOG_ROOT` or `OUTPUT_DIR` in your Python script.
- **Adjust file size:** Edit `MAX_PARTITION_SIZE` (in bytes).
- **Redis settings:** Update `REDIS_HOST`, `REDIS_PORT`, and `REDIS_DB` in script.

---

## ❗ Requirements & Notes

- **Read access to** `/var/lib/docker/containers/`
- **Docker default log driver** (`json-file`)
- **Container names must be unique**

---

## 👨‍💻 Example Output

| Filename                                   | Description                    |
|---------------------------------------------|--------------------------------|
| output/frontend-01-20240717123000.log.gz    | First partition for `frontend` |
| output/mysql-03-20240717124144.log.gz       | Third partition for `mysql`    |
| output/backend-02-20240717123550.log.gz     | Second partition for `backend` |

---

## 🤝 Contributions

PRs, issues, & feedback **welcome**!

---

**Made with ❤️ for robust, resilient container log management!**



**Tip:**  
GitHub's Mermaid support is still evolving; if you ever see issues rendering diagrams, check that you're on the [Web interface](https://github.com/) (not a local preview), and that your diagram syntax is supported per [their docs](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams#creating-mermaid-diagrams).

If you want PNG/SVG diagrams, you can export from [https://mermaid.live/](https://mermaid.live/) and include as images too! Let me know what you prefer.