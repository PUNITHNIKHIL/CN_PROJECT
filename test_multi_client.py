"""
test_multi_client.py — Simulate 3 concurrent clients uploading different files
==============================================================================
Run the server first:  python server.py
Then run this script:  python test_multi_client.py
"""

import os
import threading
import time
import logging

from client import upload

logging.basicConfig(
    level=logging.INFO,
    format="[TEST  %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("test")

SERVER = "127.0.0.1"
TEST_DIR = os.path.join(os.path.dirname(__file__), "test_files")


def make_test_file(name: str, size_kb: int) -> str:
    """Create a test file filled with pseudo-random-ish data."""
    os.makedirs(TEST_DIR, exist_ok=True)
    path = os.path.join(TEST_DIR, name)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            # write incrementing bytes pattern so corruption is detectable
            block = bytes(range(256)) * 4   # 1 KB
            for _ in range(size_kb):
                f.write(block)
    return path


def client_worker(client_id: int, filepath: str, results: dict):
    log.info(f"Client-{client_id} starting upload: {os.path.basename(filepath)}")
    t0 = time.time()
    try:
        upload(SERVER, filepath)
        results[client_id] = ("OK", time.time() - t0)
    except Exception as e:
        results[client_id] = ("FAIL", str(e))


def main():
    # Create test files of different sizes
    files = [
        make_test_file("small_1KB.bin",  1),
        make_test_file("medium_64KB.bin", 64),
        make_test_file("large_256KB.bin", 256),
    ]

    log.info("=" * 60)
    log.info("Starting 3 concurrent client uploads")
    log.info("=" * 60)

    results = {}
    threads = []
    start   = time.time()

    for i, filepath in enumerate(files):
        t = threading.Thread(
            target=client_worker,
            args=(i + 1, filepath, results),
            daemon=True,
        )
        threads.append(t)

    # Launch all simultaneously
    for t in threads:
        t.start()
        time.sleep(0.1)   # slight stagger so logs are readable

    for t in threads:
        t.join(timeout=60)

    elapsed = time.time() - start
    log.info("=" * 60)
    log.info(f"All clients finished in {elapsed:.2f}s")
    for cid, result in results.items():
        status, detail = result
        if status == "OK":
            log.info(f"  Client-{cid}: ✓ OK ({detail:.2f}s)")
        else:
            log.error(f"  Client-{cid}: ✗ FAILED — {detail}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
