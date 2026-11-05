# Solomon C101 benchmark

## Reproduce

From `backend/`, run:

```powershell
.\venv\Scripts\python.exe -m app.services.student_routing.solomon_benchmark data/solomon/C101.txt --iterations 300 --seed 42
```

The instance file is the standard Solomon C101 text format. The adapter reads
fleet count, capacity, coordinates, demand, ready/due times, and each customer's
service time. Both distance and travel time use Euclidean distance, as required
by the Solomon benchmark. Service starts after arrival or the ready time,
whichever is later, and must start no later than the due time. The depot closing
time is checked on return.

The C101 evaluator was validated against the detailed 10-route solution
published by [SINTEF](https://www.sintef.no/projectweb/top/vrptw/100-customers/):
it calculates 10 vehicles, distance 828.94, and zero capacity and time-window
violations. Objective priority is feasibility, then vehicle count, then distance.

Tabu uses the project's existing 2-opt, swap, and relocate moves. The Solomon
runner samples up to 80 move descriptors uniformly before copying candidate
routes; the base optimizer copies every move before sampling, which made the
first 100-customer run needlessly slow. This keeps the same sampled move set and
search policy while avoiding those discarded copies.

## Run result

Environment: project `backend/venv`, seed 42, 300 Tabu iterations.

| Measure | Sweep seed | Sweep + Tabu |
|---|---:|---:|
| Vehicles | 10 | 10 |
| Euclidean distance | 1,411.57 | 2,896.41 |
| Capacity violations | 0 | 0 |
| Time-window violations | 87 | 22 |
| Total lateness (minutes) | 63,936.90 | 12,440.23 |
| All 100 customers exactly once | Yes | Yes |
| Feasible | No | No |
| Runtime | — | 9.649 s |

Published C101 BKS: **10 vehicles, distance 828.94**. The candidate is
infeasible, so its distance gap is not meaningful and is intentionally omitted.
This run validates the converter/evaluator and shows that the current Sweep
initialization plus Tabu search does not solve C101 to feasibility. Its lateness
penalty encourages repairing time windows, but the resulting routes are much
longer. Finding a feasible benchmark-quality solution will require a stronger
Solomon-specific construction or repair heuristic and likely a distance-aware
search strategy after feasibility.
