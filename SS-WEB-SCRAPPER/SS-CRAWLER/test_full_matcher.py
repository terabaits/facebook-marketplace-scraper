# -*- coding: utf-8 -*-
"""Test the full ComputerMatcher with actual listing text."""
import sys
sys.path.insert(0, 'src')

from src.scraper.computer_matcher import ComputerMatcher
from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository,
    MotherboardRepository, MonitorRepository
)
from src.utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig()
init_database(config.database)
db = get_db_manager()

# Actual listing text from SS.COM
title = "Datori un orgtehnika/Datori/ Pardod"
description = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Mat. pl. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele."""

full_text = f"{title} {description}".strip()

print("Testing ComputerMatcher with actual listing:")
print("="*60)
print(f"Full text (first 200 chars): {full_text[:200]}...")
print()

# Load all components
with db.get_session() as session:
    cpus = CPUReferenceRepository.get_all(session)
    gpus = GPUReferenceRepository.get_all(session)
    rams = RAMReferenceRepository.get_all(session)
    ssds = SSDReferenceRepository.get_all(session)
    psus = PSURepository.get_all(session)
    cases = CaseRepository.get_all(session)
    motherboards = MotherboardRepository.get_all(session)
    monitors = MonitorRepository.get_all(session)
    
    print(f"Loaded: {len(cpus)} CPUs, {len(gpus)} GPUs, {len(rams)} RAMs, {len(ssds)} SSDs")
    print(f"        {len(psus)} PSUs, {len(cases)} Cases, {len(motherboards)} Motherboards, {len(monitors)} Monitors")
    
    # Create matcher
    matcher = ComputerMatcher(
        cpus=cpus, gpus=gpus, rams=rams, ssds=ssds,
        psus=psus, cases=cases, motherboards=motherboards, monitors=monitors
    )
    
    # Match the listing
    result = matcher.match(title, description)
    
    # Print results
    print("\n" + "="*60)
    print("MATCH RESULTS:")
    print("="*60)
    
    if result.cpu:
        print(f"CPU: {result.cpu.get('name', 'N/A')} (ID: {result.cpu.get('id')}, conf: {result.cpu_confidence})")
    else:
        print("CPU: Not matched")
    
    if result.gpu:
        print(f"GPU: {result.gpu.get('name', 'N/A')} (ID: {result.gpu.get('id')}, conf: {result.gpu_confidence})")
    else:
        print("GPU: Not matched")
    
    if result.ram:
        print(f"RAM: {result.ram.get('name', 'N/A')} (ID: {result.ram.get('id')}, conf: {result.ram_confidence}, method: {result.ram_method})")
    else:
        print("RAM: Not matched")
    
    if result.ssd:
        print(f"SSD: {result.ssd.get('name', 'N/A')} (ID: {result.ssd.get('id')}, conf: {result.ssd_confidence})")
    else:
        print("SSD: Not matched")
    
    if result.motherboard:
        print(f"Motherboard: {result.motherboard.get('brand', 'N/A')} {result.motherboard.get('model', 'N/A')} (ID: {result.motherboard.get('id')}, conf: {result.motherboard_confidence}, method: {result.motherboard_method})")
    else:
        print("Motherboard: Not matched")
    
    if result.monitor:
        print(f"Monitor: {result.monitor.get('brand', 'N/A')} {result.monitor.get('model', 'N/A')} (ID: {result.monitor.get('id')}, conf: {result.monitor_confidence}, method: {result.monitor_method})")
    else:
        print("Monitor: Not matched")

print("\n" + "="*60)
print("EXPECTED:")
print("  RAM: G.Skill Aegis 32 GB (ID 1979)")
print("  Motherboard: Gigabyte H310M S2H 2.0 (ID 8231)")
print("  Monitor: AOC 25\" LCD 2590G4 (or similar AOC monitor)")
