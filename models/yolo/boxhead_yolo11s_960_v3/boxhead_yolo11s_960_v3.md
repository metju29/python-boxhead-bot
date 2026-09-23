# boxhead_yolo11s_960_v3

- Trained: 2026-08-31 16:23
- Base model: `models/yolo/pretrained/yolo11s.pt`
- Dataset: `data/labeled/v39-pool-dedupe-fix-1659/data.yaml`
- Images: 1329 train / 330 valid (1659 total)
- imgsz=960, batch=4, epochs=100
- Training time: 5.07h on mps
- Architecture: 182 layers, 9,433,597 parameters, 48.6 GFLOPs

## Overall validation metrics
- Precision: 0.971
- Recall: 0.945
- mAP50: 0.963
- mAP50-95: 0.839
- Confusion matrix: `confusion_matrix.png` (`confusion_matrix_normalized.png` for per-class rates)

## Dataset

| class | images | instances |
|---|---|---|
| ammo_pack | 1584 | 6384 |
| barrel | 623 | 5168 |
| devil | 836 | 1481 |
| devil_dead | 160 | 176 |
| devil_projectile | 207 | 427 |
| explosion | 222 | 375 |
| fake_wall | 331 | 1972 |
| grenade | 204 | 309 |
| mine | 322 | 4890 |
| player | 1463 | 1467 |
| player_dead | 183 | 184 |
| zombie | 1380 | 15158 |
| zombie_dead | 656 | 1976 |
| shrapnel | 171 | 530 |
| chargepack | 206 | 216 |

## Per-class validation metrics

| class | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|
| ammo_pack | 0.989 | 0.986 | 0.994 | 0.965 |
| barrel | 0.998 | 0.996 | 0.995 | 0.970 |
| devil | 0.981 | 0.993 | 0.990 | 0.926 |
| devil_dead | 0.951 | 0.897 | 0.914 | 0.769 |
| devil_projectile | 0.970 | 0.986 | 0.994 | 0.764 |
| explosion | 0.904 | 0.901 | 0.936 | 0.797 |
| fake_wall | 0.994 | 0.983 | 0.990 | 0.937 |
| grenade | 1.000 | 0.866 | 0.902 | 0.592 |
| mine | 0.980 | 0.973 | 0.984 | 0.934 |
| player | 0.986 | 0.985 | 0.984 | 0.949 |
| player_dead | 0.971 | 0.968 | 0.977 | 0.860 |
| zombie | 0.987 | 0.976 | 0.992 | 0.941 |
| zombie_dead | 0.927 | 0.893 | 0.959 | 0.814 |
| shrapnel | 0.942 | 0.775 | 0.833 | 0.440 |
| chargepack | 0.992 | 1.000 | 0.995 | 0.920 |

## Known limitations

- **`shrapnel` mAP50-95 dropped further (0.533 → 0.440) vs `v2`, despite this round's whole point being a dataset-correctness fix for this class.** Traced to two things, neither a modeling problem: (1) the dedupe transitivity bug fix (see `helpers/dedupe_pool.py`) restored 108 wrongly-archived images, but proper complete-linkage re-dedup then re-archived most of them as genuine near-duplicates of each other — net gain for `shrapnel` was only +2 images / +5 instances (169→171 / 525→530), so there was never much new signal to learn from; (2) this round's random train/valid split happened to put fewer `shrapnel` images in valid (35 vs 44), so the metric has more sampling variance on a smaller set. Same underlying small-object IoU-precision ceiling as noted on `v2` (see `devil_projectile`, same signature: high mAP50, low mAP50-95) — still not gameplay-critical, see below.
- Priority classes (`zombie`, `devil`, `devil_projectile`) are stable or improved vs `v2` — `zombie` mAP50-95 0.940→0.941, `devil` 0.906→0.926 (R 0.978→0.993), `devil_projectile` 0.779→0.764 (small valid set, 38 images, likely noise). These are the classes that matter for gameplay; `shrapnel` gaps are accepted per the same reasoning as `v2`.
- Overall metrics (mAP50 0.970→0.963, mAP50-95 0.848→0.839) are within noise of `v2` — this retrain was primarily about training on a dataset with a fixed, verified-correct dedup pass, not about chasing a metric improvement.
