# BDP-GARDM

Pilot implementation scaffold for the BDP-GARDM research pipeline.

## Development sequence

1. Foundation and configuration
2. Schema contracts
3. Data ingestion and validation
4. Incident/context assembly
5. AG01 Monitoring
6. AG02 Diagnosis
7. AG03 Governance/Risk
8. GARDM decision engine
9. Recovery/HITL
10. AG05 Validation
11. Audit and memory
12. Synthetic expert interface
13. Single-incident end-to-end test
14. 100-incident pilot
15. Experiment runner, baselines, ablations and metrics

## Run

Install dependencies:

    pip install -r requirements.txt

Run foundation check:

    python run_pipeline.py

Run tests:

    pytest -q
