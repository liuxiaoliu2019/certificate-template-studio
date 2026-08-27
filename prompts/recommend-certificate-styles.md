# 推荐三种证书风格 Prompt

## 前置条件

- 已生成 Style DNA；
- 已生成角色身份档案；
- 用户已手动输入证书标题；
- 已读取 `references/certificate-style-library.md` 与 `references/style-compatibility-scoring.md`。

## 输入

- Style DNA：`{style_dna}`
- 角色身份档案：`{character_identity}`
- 用户标题：`{certificate_title}`
- 输出 schema：`schemas/style_recommendation.schema.json`

## Prompt

对证书风格库中的 7 个风格家族逐一进行兼容性评分。权重固定为：画风 35、核心元素 25、色彩 20、整体气质 15、原构图可转化性 5。每项给整数分并写出基于 Style DNA 的具体理由。

总分低于 70 的原始配置不能入选。如果达到 70 的家族不足三个，可以进行受控风格转译后重新评分；转译后仍低于 70 则排除。摄影或写实封面允许转为扁平、手绘、水彩或线稿，但必须保留核心元素、配色关系和气质。

选择三个不同的风格家族，并为每个候选建立完整 Style Profile。三个 Profile 必须分别使用 `cover_character_led`、`balanced_translation`、`frame_led`。默认第 3 个为 `frame_led + full_frame + textbook_fusion=conservative`，可不使用角色；它的教材兼容主要通过配色、年龄感、气质和少量主题符号判断，不以封面人物数量判断。前两个 Profile 不得同时都使用 `full_frame`。

任意两个 Profile 至少有三个核心参数不同；差异不能仅来自颜色、字体或小装饰。含角色候选必须在策略中列出实际使用的 `character_id`，并声明加载对应原图裁切与身份锁。标题长度只影响后续排版，不影响兼容性分数。

只返回符合 schema 的 JSON。三套候选不得生成图片，先完成评分、设计角色、边框结构、策略和差异检查。
