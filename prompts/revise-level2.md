# LEVEL2 中改 Prompt

## 输入

- 当前方案：`{current_artifact}`
- 教材封面：`{cover_path}`
- 对应控制图：`{control_path}`
- Style DNA：`{style_dna}`
- 唯一标题：`{certificate_title}`
- 用户反馈：`{feedback}`
- 当前 Style Profile：`{style_profile}`
- 角色身份档案与本方案裁切：`{character_identity_and_refs}`
- 允许变化的 Profile 参数：`{allowed_parameter_changes}`

## Prompt

基于当前证书方案生成一个中度重构变体。锁定当前 Style Profile 的风格家族、标题原文、中央功能区和主要视觉语言，只允许调整 `{allowed_parameter_changes}`，并按用户反馈重新组织布局关系：{feedback}。

允许重新安排人物、标题周边、边缘装饰和落款功能区边界；不要退回到完全不同的设计方向。继续把项目控制图理解为 Z80/Z50/Z20/Z12/Z08 的软性密度秩序，遵循其实际灰阶分布，不复制其灰阶或形状，也不以文字指令覆盖控制图。

人物可以移动、改变姿势或朝向，但身份锁不可解除。对照完整封面、对应原图裁切与身份档案，保持头部/发型、脸部、肤色或毛羽色、服装款式与分区配色、物种、身体比例和标志性配件。`frame_led` 仍必须保持四边连续完整边框；中改不得把完整边框拆成零散角花。

唯一可读文字为“{certificate_title}”，必须完整准确。完整标题外接框中心必须锁定在画布水平中轴 x=50%；竖版标题继续执行相对原 V3 基准向上 1.5 cm 的固定规则。不得生成任何其他文字或伪文字。中央正文安全区和右下偏内侧落款/盖章区必须实际可用；右下最外沿必须有克制的视觉收边，不得形成孤立白洞。整体仍像证书而不是海报。
