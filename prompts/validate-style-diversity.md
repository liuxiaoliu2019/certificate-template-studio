# 三方案风格差异验证 Prompt

## 输入

- 三份 Style Profile：`{style_profiles}`
- 三套方向策略：`{concept_strategies}`

## Prompt

在生图前验证三套方向是否真正不同：

1. 三个 `style_family` 必须互不相同。
2. 三个 `concept_role` 必须依次覆盖 `cover_character_led`、`balanced_translation`、`frame_led`。
3. `frame_led` 必须使用 `full_frame + textbook_fusion=conservative`；前两套不得同时都是完整边框。
4. 任意两个 Profile 至少有三个核心参数不同。
5. 边框结构与语言、插画媒介、主视觉组织、装饰密度、对称方式、角色使用、背景材质和典礼感中，至少三个维度形成可见差异。
6. 仅换颜色、标题字体、标题处理模式或小装饰不算差异。
7. 三套都必须遵守同一控制图的区域秩序。角色主导型通过身份锁保留教材识别；边框主导型可主要通过配色、年龄感、气质和少量主题符号保持联系。

若失败，返回失败原因和需要重配的参数，不要生成图片。若通过，输出每一对 Profile 的差异参数和 `passed=true`，供 `style_recommendation.json` 记录。
