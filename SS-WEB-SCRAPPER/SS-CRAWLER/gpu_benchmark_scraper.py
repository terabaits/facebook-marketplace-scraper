"""
Scraper for PassMark Video Card Benchmarks - GPU Mega Page.

Collects GPU benchmark data from https://www.videocardbenchmark.net/GPU_mega_page.html
and saves it to CSV. The page loads data via DataTables ajax from /data; we use
undetected-chromedriver to obtain a valid session, then fetch the JSON endpoint with
requests.
"""
import csv
import json
import os
import re
import sys
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup

# Reuse chrome-version helper from the existing Cinebench scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cpu-spec-dataset', 'CPU-BENCHMARKS'))
from cinebench_r26_scraper import get_chrome_version  # noqa: E402

import undetected_chromedriver as uc  # noqa: E402


class GPUBenchmarkScraper:
    """Scrapes PassMark GPU Mega Page benchmark data."""

    MAIN_URL = "https://www.videocardbenchmark.net/GPU_mega_page.html"
    DATA_URL = "https://www.videocardbenchmark.net/data"

    CSV_COLUMNS = [
        "passmark_id",
        "name",
        "g3d_mark",
        "g2d_mark",
        "tdp_w",
        "vram_mb",
        "category",
        "bus_interface",
        "max_memory_mb",
        "core_clock_mhz",
        "mem_clock_mhz",
        "rank",
        "samples",
        "price_usd",
        "release_date",
        "passmark_href",
    ]

    def __init__(self, output_path: Optional[str] = None, headless: bool = True):
        self.output_path = output_path or "gpu_benchmark_reference.csv"
        self.headless = headless
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
            ),
            "Referer": self.MAIN_URL,
            "X-Requested-With": "XMLHttpRequest",
        })

    def _init_driver(self) -> uc.Chrome:
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        chrome_ver = get_chrome_version()
        if chrome_ver:
            return uc.Chrome(options=options, version_main=chrome_ver)
        return uc.Chrome(options=options)

    def _extract_session(self) -> None:
        """Open the main page with a real browser to obtain cookies/session."""
        driver = None
        try:
            driver = self._init_driver()
            driver.get(self.MAIN_URL)
            for cookie in driver.get_cookies():
                self.session.cookies.set(cookie["name"], cookie["value"])
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _parse_int(self, value: Any) -> Optional[int]:
        if value is None or value == "NA":
            return None
        try:
            return int(re.sub(r"[^0-9-]", "", str(value)))
        except ValueError:
            return None

    def _parse_float(self, value: Any) -> Optional[float]:
        if value is None or value == "NA":
            return None
        try:
            cleaned = re.sub(r"[^0-9.\-]", "", str(value))
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch GPU benchmark records from the /data endpoint."""
        self._extract_session()
        response = self.session.get(self.DATA_URL, timeout=120)
        response.raise_for_status()

        payload = response.json()
        raw_records = payload.get("data", [])
        print(f"[INFO] Fetched {len(raw_records)} raw records from PassMark")

        records = []
        for row in raw_records:
            # memSize may contain values like "4096 MB" or "NA"
            vram_mb = self._parse_int(row.get("memSize"))
            max_mem_mb = self._parse_int(row.get("memSize"))
            core_clk = self._parse_int(row.get("coreClk"))
            mem_clk = self._parse_int(row.get("memClk"))
            samples = self._parse_int(row.get("samples"))
            rank = self._parse_int(row.get("rank"))
            tdp = self._parse_int(row.get("tdp"))

            records.append({
                "passmark_id": row.get("id"),
                "name": row.get("name"),
                "g3d_mark": self._parse_int(row.get("g3d")),
                "g2d_mark": self._parse_int(row.get("g2d")),
                "tdp_w": tdp,
                "vram_mb": vram_mb,
                "category": row.get("cat"),
                "bus_interface": row.get("bus") if row.get("bus") != "NA" else None,
                "max_memory_mb": max_mem_mb,
                "core_clock_mhz": core_clk,
                "mem_clock_mhz": mem_clk,
                "rank": rank,
                "samples": samples,
                "price_usd": self._parse_float(row.get("price")),
                "release_date": row.get("date") if row.get("date") != "NA" else None,
                "passmark_href": row.get("href"),
            })

        return records

    def save_csv(self, records: List[Dict[str, Any]]) -> str:
        """Save records to CSV and return the file path."""
        path = os.path.abspath(self.output_path)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(records)
        print(f"[INFO] Saved {len(records)} records to {path}")
        return path

    def run(self) -> str:
        records = self.fetch_data()
        return self.save_csv(records)


if __name__ == "__main__":
    scraper = GPUBenchmarkScraper()
    scraper.run()
