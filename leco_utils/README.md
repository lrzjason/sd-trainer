# LECO
platdev氏の[LECO](https://github.com/p1atdev/LECO)を参考に、色々変更を加えて実装したものになります。

解説記事はこちらになります。https://zenn.dev/aics/articles/lora_for_erasing_concepts_from_diffusion_models

originalのリポジトリはhttps://github.com/rohitgandikota/erasing になります。

# 設定ファイルについて
[leco_utils/config/example.yaml](https://github.com/laksjdjf/sd-trainer/blob/dev/leco_utils/config/example.yaml)に例があります。モデルはdiffusers形式でもckpt or safetensorsでもおっけーです。

prompts.yamlの文法
```
target: "意味を変えたい対象"
positive: "近づけたい（または遠ざけたい）意味"
negative: "学習中に使うネガティブプロンプト（どんなことになるか想像つかない）"
neutral: "基本設定しなくていいと思います。"
guidance_scale: どれくらい近づけるか（マイナスにすると遠ざかる）
```

例１：
```
target: "real life"
guidance_scale: -1
```
positiveは省略するとtargetと同じになります。つまりこの例では"real life"が自分自身の意味から離れていきます。そのため"real life"という単語で実写画像が生成できなくなります。


例２：
```
target: "1girl"
positive: "1girl futanari"
guidance_scale: 1
```
この例では"1girl"の意味が"1girl futanari"に近づいていきます。これによって特に指定しなくても勝手におちｎ****

例３：
```
target: ""
positive: "masterpiece, best quality"
negative: "low quality"
neutral: ""
guidance_scale: 3
```
この例では修飾プロンプトを省略できるようなLoRAができるかもしれません。negativeにはネガティブプロンプトが入れられますが、
guidance scaleがマイナス（つまりpositiveから遠ざけたいとき）はネガティブプロンプトに近づくよう学習してしまうので非推奨です。
neutralはとりあえず考えなくていいんじゃないかな。

訓練は以下みたいな感じでできます。
```
pytbon leco.py leco_utils/config/example.yaml
```

# 変更点

+ LECOでは学習用の画像をあらかじめつくるのではなく、学習中に画像を生成します。
学習時にランダムにステップ数を決めて、そのステップ数分ノイズ除去した画像を使います。この処理に時間がかかるため、私の実装ではノイズ除去ループ中の途中結果も学習に使うようにしました。1回のループで何回分の画像を使うかがnum_samplesで設定できます。あげれば学習速度が上がりますが、精度はさがるかもしれません。学習時間削減効果は多分```2/(num_samples+1)```です。

+ LoRAの実装はKohya氏のものと少し違うので、なんかでエラーが起こるかもしれません。

+ 本実装ではとびとびのtimestepしか学習できませんが、この実装は全てのtimestepが学習できるようになっています（あまり自信ないけど）。


