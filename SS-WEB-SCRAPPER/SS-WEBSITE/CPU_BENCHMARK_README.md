# CPU Benchmark Database Integration

This system imports benchmark data from CSV files and links them to `CPU_REFERENCE` via fuzzy name matching.

## Files Created

### 1. `cpu_benchmark_schema.sql`
Creates all necessary tables and views:
- `cpu_benchmarks_r23` - Cinebench R23 scores
- `cpu_benchmarks_r26` - Cinebench 2026 scores  
- `cpu_benchmarks_passmark` - PassMark benchmark data
- `cpu_prices_pcpartpicker` - PCPartPicker pricing
- `cpu_name_matches` - Fuzzy matching results
- `cpu_complete_data` - Combined view with all data
- Various analytics views

### 2. `import_cpu_benchmarks.py`
Imports CSV data and performs fuzzy matching:
```bash
python import_cpu_benchmarks.py
```

**Steps:**
1. Imports all 4 CSV files
2. Performs fuzzy name matching (60%+ similarity)
3. Links matches to CPU_REFERENCE
4. Generates analytics report
5. Exports unmatched CPUs

### 3. `cpu_benchmark_analytics.py`
Detailed analytics dashboard:
```bash
python cpu_benchmark_analytics.py
```

**Reports:**
- Match success rates by source
- Data completeness scores
- Unmatched CPU analysis
- Multiple match detection
- Benchmark leaderboards
- Price-performance analysis

## Usage

### Step 1: Run the Schema
```bash
psql -h localhost -p 5433 -U crawler -d ss_market -f cpu_benchmark_schema.sql
```

### Step 2: Import Data
```bash
python import_cpu_benchmarks.py
```

### Step 3: View Analytics
```bash
python cpu_benchmark_analytics.py
```

## Key Queries

### View Complete CPU Data
```sql
SELECT * FROM cpu_complete_data 
WHERE producer = 'Intel' 
AND data_completeness_score >= 3;
```

### Find CPUs Missing Benchmarks
```sql
SELECT cpu_name, processor_number 
FROM cpu_unmatched_analysis 
WHERE producer = 'AMD';
```

### Best Price-Performance
```sql
SELECT cpu_name, pcpartpicker_price, cinebench_r23_multi,
       pcpartpicker_price / cinebench_r23_multi as price_per_point
FROM cpu_complete_data
WHERE pcpartpicker_price IS NOT NULL 
AND cinebench_r23_multi IS NOT NULL
ORDER BY price_per_point ASC
LIMIT 10;
```

### Match Summary
```sql
SELECT * FROM cpu_match_summary;
```

## Data Sources

| File | Records | Source |
|------|---------|--------|
| cinebench_r23_scores.csv | 695 | cpu-monkey.com |
| cinebench_r26_scores.csv | 220 | cpu-monkey.com |
| benchmark-cpus.csv | 6,571 | cpubenchmark.net |
| cpu_pricesV2.csv | 887 | PCPartPicker |

## Fuzzy Matching

- **Algorithm**: SequenceMatcher (difflib)
- **Threshold**: 60% similarity minimum
- **Normalization**: Removes extra spaces, standardizes AMD/Intel naming
- **Per-CPU**: Best match from each source saved independently

## Unmatched CPUs

Unmatched CPUs are exported to:
```
cpu-spec-dataset/Results/unmatched_cpus.csv
```

Use this for:
- Manual name mapping
- Identifying missing benchmarks
- Data quality improvement
