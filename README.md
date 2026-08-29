# Data Shape Guard

JSON / JSONL の実データからデータ形状を推定し、baseline と current の**型変更・フィールド消失・出現率ドリフト**を検出する無料OSSです。

```bash
python data_shape_guard.py infer sample.jsonl
python data_shape_guard.py compare before.jsonl after.jsonl
```

- ネストした object / array に対応
- required 比率を実データから推定
- HTML + JSON レポート
- Python 3.10+ / 外部依存なし / MIT
- 入力データは変更しません

OSS: https://github.com/paper-daemon/data-shape-guard
作者サイト: https://paper-daemon.github.io/
