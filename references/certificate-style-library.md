# 证书风格库

在推荐三套横版方向或 LEVEL3 更换风格时读取本文件。风格家族定义“证书如何表达”，教材 Style DNA 继续定义“画什么、用什么颜色、呈现什么气质”。

## S01_classic_ceremonial_gold｜经典典礼金纹

- 语言：米白或象牙白纸张、金色细线、月桂、勋章、角花、轻纸张肌理、对称秩序。
- 适用：结业、优秀学员、正式竞赛、学院型教材。
- 约束：金纹不可堆满中央；不要生成仿官方印章或机构徽标。
- 常用参数：`medium|rich`、`symmetric`、`paper_texture|line_art`、`standard|grand`、`none|corner_character`。

## S02_modern_academic_geometry｜现代学院几何

- 语言：干净背景、细线框、少量几何模块、大留白、平衡不对称。
- 适用：青少年、语言课程、现代教育、摄影或混合媒介教材的插画化转译。
- 约束：只取教材 2 至 4 个主色；几何模块不得挤偏标题。
- 常用参数：`light|medium`、`symmetric|balanced_asymmetric`、`flat|line_art`、`light|standard`、`none|edge_scene`。

## S03_dark_premium_technology｜深色尊贵科技

- 语言：深蓝、炭黑或深紫满版，配金、银或亮蓝细线；抽象光线、粒子、波纹、网格。
- 适用：科技、编程、商务英语、高级赛事、现代城市主题。
- 约束：低龄柔和教材若适配后仍低于 70 分不得使用；控制光效，保证变量区可排版。
- 常用参数：`light|medium`、`symmetric|balanced_asymmetric`、`line_art`、`standard|grand`、`none|edge_scene`。

## S04_fresh_botanical_watercolor｜清新自然水彩

- 语言：水彩植物、花朵、天空、森林或薄颜料晕染；外围生长、中央通透。
- 适用：自然、成长、语言学习、温柔童趣、毕业季。
- 约束：左右主体保持可见；连接部分可渐弱，但不得把右下做成孤立白洞。
- 常用参数：`light|medium|rich`、`symmetric|balanced_asymmetric`、`watercolor|hand_drawn`、`light|standard`、`corner_character|edge_scene`。

## S05_childrens_flat_education｜儿童扁平教育

- 语言：圆润形状、鲜明配色、卡通角色、动物与学习用品；可用云朵、波浪或不规则中央面板。
- 适用：幼儿园、小学、少儿英语、启蒙课程。
- 约束：角色从边缘探入，不侵占标题和变量区；控制数量，避免变成儿童活动海报。
- 常用参数：`medium|rich`、`symmetric|balanced_asymmetric`、`flat|hand_drawn`、`light|standard`、`corner_character|edge_scene`。

## S06_themed_dynamic_event｜主题动态赛事

- 语言：体育、科学、艺术、音乐或探索器材，配方向线、运动轨迹和局部场景。
- 适用：竞赛、营地、专项课程、主题活动。
- 约束：主题视觉退到边缘；若中央出现大 KV、口号层级或海报式信息则失败。
- 常用参数：`medium|rich`、`balanced_asymmetric`、`flat|hand_drawn|line_art`、`light|standard`、`edge_scene`。

## S07_chinese_ceremonial_award｜中式典礼奖状

- 语言：红、金、暖米色，搭配简化传统纹样、帷幕、星徽或祥云；强调水平秩序和中央轴线。
- 适用：中文学校奖状、表彰、正式结业。
- 约束：不得仿制官方机关徽记、印章或特定学校标识；传统元素应概括化。
- 常用参数：`medium|rich`、`symmetric`、`paper_texture|line_art`、`standard|grand`、`none|corner_character`。

## 共用不变量

- 唯一可读文字是用户标题。
- 标题外接框水平中心为画布 `x=50%`；竖版另执行向上 1.5 cm。
- 左右下角均保留清晰视觉锚点，并用由大到小的同风格元素形成弱连接。
- 风格骨架不得覆盖控制图的区域秩序，也不得复制控制图形状。
- 摄影或写实教材允许转译为选定的插画媒介，但核心元素、色彩关系和气质必须可识别。

## 跨家族边框结构

边框是版式轴，不是单独风格家族。S01、S02、S04、S05、S07 等均可采用完整边框，但必须使用本家族的材质和造型语言。

- `full_frame`：四边连续完整边框，角部强化；适合边框主导方案。
- `corner_connected`：角花或角部模块通过线条、纹样连接。
- `open_frame`：局部开口，但证书边界仍清晰。
- `illustrated_perimeter`：用外围插画形成边界，不使用传统线框。

可选边框语言：`classic_double_line`、`european_ornamental`、`modern_geometric`、`botanical_vine`、`storybook_sculpted`。只借鉴一般语法，不复制参考奖状的具体花纹、徽章、文字或完整构图。

默认三方案中的 `frame_led` 必须使用 `full_frame`，并将 `textbook_fusion` 设为 `conservative`。它可以不使用人物，主要通过教材配色、年龄感和少量主题符号保持协调。
