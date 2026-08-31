# boxhead_yolo11s_960_v2

- Trained: 2026-08-31 08:46
- Base model: `models/yolo/pretrained/yolo11s.pt`
- Dataset: `data/labeled/v38-pool-1603/data.yaml`
- Images: 1283 train / 320 valid (1603 total)
- imgsz=960, batch=4, epochs=100
- Training time: 6.29h on mps
- Architecture: 182 layers, 9,433,597 parameters, 48.6 GFLOPs

## Overall validation metrics
- Precision: 0.972
- Recall: 0.942
- mAP50: 0.970
- mAP50-95: 0.848
- Confusion matrix: `confusion_matrix.png` (`confusion_matrix_normalized.png` for per-class rates)
- Curves: `BoxPR_curve.png`, `BoxF1_curve.png`, `results.png`

## Per-class dataset stats + validation metrics

| class | images | instances | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| ammo_pack | 1530 | 6146 | 0.993 | 0.978 | 0.994 | 0.957 |
| barrel | 585 | 4781 | 0.996 | 0.989 | 0.995 | 0.956 |
| devil | 819 | 1457 | 0.978 | 0.978 | 0.991 | 0.906 |
| devil_dead | 157 | 173 | 0.969 | 0.907 | 0.938 | 0.797 |
| devil_projectile | 207 | 427 | 0.993 | 1.000 | 0.995 | 0.779 |
| explosion | 219 | 369 | 0.929 | 0.884 | 0.942 | 0.794 |
| fake_wall | 323 | 1933 | 0.998 | 0.978 | 0.985 | 0.953 |
| grenade | 196 | 289 | 0.966 | 0.853 | 0.907 | 0.643 |
| mine | 316 | 4824 | 0.993 | 0.983 | 0.995 | 0.935 |
| player | 1436 | 1440 | 0.984 | 0.990 | 0.995 | 0.948 |
| player_dead | 154 | 155 | 0.963 | 0.969 | 0.969 | 0.823 |
| zombie | 1327 | 14750 | 0.990 | 0.976 | 0.993 | 0.940 |
| zombie_dead | 640 | 1941 | 0.935 | 0.922 | 0.967 | 0.852 |
| shrapnel | 169 | 525 | 0.911 | 0.822 | 0.898 | 0.533 |
| chargepack | 205 | 215 | 0.978 | 0.909 | 0.987 | 0.910 |

## Known limitations

- **`shrapnel` mAP50-95 capped around 0.53** despite decent mAP50 (0.898) and complete-enough labeling — confirmed via a box-tightness audit (`helpers/dataset_qa/audit_box_tightness.py`, see `reports/v38-pool-1603/box_tightness_shrapnel/`) that boxes are tight and clusters are labeled, not a data defect. Fragments are only a few dozen pixels with soft edges, so this is an inherent small-object IoU-precision ceiling (same signature as `devil_projectile`: R=1.000, mAP50=0.995, mAP50-95=0.779). Not expected to improve much without more data / imgsz increase / bigger model.
- Not being chased further: `shrapnel` isn't gameplay-critical — partial recall on a fragment cluster still signals "explosion hazard here" to the bot. `zombie`/`devil`/`devil_projectile` are the priority classes for detection quality; all three are strong on this model.
