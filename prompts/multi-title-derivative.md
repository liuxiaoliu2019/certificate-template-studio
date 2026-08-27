# 同教材多标题衍生 Prompt

## 前置条件

- 有已批准 Master；
- 用户没有明确要求重新设计或再出三套；
- 新标题来自用户手动输入。

## 输入

- 已批准 Master：`{master_artifact}`
- 原标题：`{master_title}`
- 新标题：`{new_title}`
- Style DNA：`{style_dna}`
- Master Style Profile：`{master_style_profile}`
- Master 角色身份档案与裁切：`{character_identity_and_refs}`
- 对应控制图：`{control_path}`

## Prompt

基于已批准 Master 和 Master Style Profile 生成同系列的新标题版本。锁定风格家族、核心参数、主体构图、角色/核心元素、主色、左右角锚点、边缘弱连接、正文安全区和落款功能区。

若 Master 含教材角色，角色身份也必须锁定，对照原封面、裁切和身份档案，不得因替换标题而重绘脸部、发型、服装、毛羽色、物种、比例或配件。若 Master 为完整边框型，保持边框结构和语言，不得退化为角花。

将唯一可读标题从“{master_title}”替换为“{new_title}”。允许仅为适应新标题字数而调整标题字号、字宽、字距、必要换行和标题周围少量陪衬装饰；不得重排主体、改变整体配色、风格家族或探索新方向。无论标题字数或行数如何变化，组合标题外接框中心必须锁定在画布水平中轴 x=50%；竖版继续执行相对原 V3 基准向上 1.5 cm 的固定位置规则。

“{new_title}”必须逐字准确并与原 Master 的标题视觉属于同一系列。除新标题外禁止任何可读或疑似文字。控制图只作为隐藏区域密度参考，不复制其灰阶或形状。

输出与 Master 同方向、同尺寸的完整证书背景图。
