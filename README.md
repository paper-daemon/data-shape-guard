# Data Shape Guard

JSON / JSONL の実データからデータ形状を推定し、baseline と current の**型変更・フィールド消失・出現率ドリフト**を検出する無料OSSです。

```bash
python data_shape_guard.py infer sample.jsonl
python data_shape_guard.py compare before.jsonl after.jsonl
```

- ネストした object / array に対応
- 通常keyは `$.field`、`.` / `[]` などを含むliteral keyは `$["a.b"]` のようにescapeしてpath衝突を避ける
- 配列は先頭だけをsampleせず、全要素をshape推論へ含める
- required 比率を実データから推定
- HTML + JSON レポート
- Python 3.10+ / 外部依存なし / MIT
- 入力データは変更しません

51番目以降で初めて現れる型も見逃さないよう、配列要素を黙って切り捨てない方針です。

```bash
python3 -m unittest -v tests.test_data_shape_guard
```

OSS: https://github.com/paper-daemon/data-shape-guard
作者サイト: https://paper-daemon.github.io/

## BOOTH
0円配布: https://amase-memo.booth.pm/items/8778557
