import os
import subprocess
import time
import json
import yaml
import threading
import datetime
import redis
import gzip
import shutil

DOCKER_LOG_ROOT = '/var/lib/docker/containers'
OUTPUT_DIR = './output'
CONFIG_PATH = 'config.yaml' # YAML file with container names
MAX_PARTITION_SIZE = 5 * 1024 * 1024 * 1024  # 5GB

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def gzip_file(filepath):
    gz_path = filepath + ".gz"
    with open(filepath, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(filepath)  # Remove original after gzipping


def get_container_id(name):
    result = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.Id}}", name], text=True
    )
    return result.strip()

def format_time_iso8601_z(timestr):
    try:
        if timestr.endswith('Z'):
            timestr = timestr[:-1]
            if '.' in timestr:
                dt_part, ns_part = timestr.split('.')
                us_part = ns_part[:6].ljust(6, '0')
                timestr = f"{dt_part}.{us_part}"
                dt = datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                dt = datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S")
            dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        else:
            return datetime.datetime.fromisoformat(timestr).strftime("%Y-%m-%dT%H:%M:%S%z")
    except Exception as e:
        return "NA"

def get_partition_index(container_name):
    key = f"log-partition:{container_name}"
    idx = r.get(key)
    if idx is None:
        idx_str = "01"
        r.set(key, idx_str)
    else:
        idx_str = idx.decode('utf-8') if isinstance(idx, bytes) else str(idx)
    return idx_str

def set_partition_index(container_name, idx_str):
    key = f"log-partition:{container_name}"
    r.set(key, idx_str)

def get_output_path(container_name, idx_str, time_str):
    return os.path.join(OUTPUT_DIR, f"{container_name}-{idx_str}-{time_str}.log")

def stream_container_logs(container_name, cid, idx_str, now_str):
    log_path = os.path.join(DOCKER_LOG_ROOT, cid, f"{cid}-json.log")
    output_path = get_output_path(container_name, idx_str, now_str)
    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

    with open(log_path, 'r') as lfile:
        lfile.seek(0, os.SEEK_END)
        print(f"[{container_name}] Waiting for lines...")

        fout = open(output_path, 'a')
        try:
            while True:
                line = lfile.readline()
                if line:
                    file_size += len(line.encode('utf-8'))
                    if file_size > MAX_PARTITION_SIZE:
                        fout.close()
                        # Gzip the previous log file
                        try:
                            print(f"[{container_name}] Gzipping {output_path}")
                            gzip_file(output_path)
                        except Exception as gz_err:
                            print(f"[{container_name}] Error gzipping {output_path}: {gz_err}")

                        # Increment index
                        idx_num = int(idx_str)
                        idx_num += 1
                        idx_str = f"{idx_num:02d}"
                        set_partition_index(container_name, idx_str)
                        now_str = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                        output_path = get_output_path(container_name, idx_str, now_str)
                        print(f"[{container_name}] Rolling over to partition {idx_str} at {now_str}")
                        fout = open(output_path, 'a')
                        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    try:
                        j = json.loads(line)
                        timestr = j.get("time") or j.get("timestamp") or ""
                        formatted_time = format_time_iso8601_z(timestr)
                    except Exception:
                        formatted_time = "NA"
                    out_line = f"{formatted_time}, {line.strip()}\n"
                    fout.write(out_line)
                    fout.flush()
                else:
                    # Check if file was removed! (broken link, pruned, etc.)
                    if not os.path.exists(log_path):
                        print(f"[{container_name}] Log file disappeared, exiting inner loop.")
                        break
                    time.sleep(0.1)
        finally:
            fout.close()

def stream_log(container_name):
    idx_str = get_partition_index(container_name)
    now_str = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    while True:
        try:
            # Try to resolve (may fail if container name doesn't exist right now)
            cid = get_container_id(container_name)
            log_path = os.path.join(DOCKER_LOG_ROOT, cid, f"{cid}-json.log")
            print(f"[{container_name}] Log path: {log_path}")

            # Wait for file to appear (if container just started)
            while not os.path.exists(log_path):
                print(f"[{container_name}] Log file {log_path} not found, retrying in 5s...")
                time.sleep(5)

            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)

            stream_container_logs(container_name, cid, idx_str, now_str)

            # If we reach here, the log file likely disappeared (container pruned/stopped/new id)
            print(f"[{container_name}] Log stream ended or file missing. Will retry in 30s.")
            time.sleep(30)
            # On new container, index handling may vary -- re-resolve from Redis.
            idx_str = get_partition_index(container_name)
            now_str = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        except Exception as err:
            print(f"[{container_name}] Error: {err} (retrying in 30s)")
            time.sleep(30)

def main():
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    container_names = config.get('containers', [])
    threads = []
    for cname in container_names:
        th = threading.Thread(target=stream_log, args=(cname,), daemon=True)
        th.start()
        threads.append(th)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping all log streams...")

if __name__ == "__main__":
    main()

