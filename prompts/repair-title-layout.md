# 标题单次自动修正

每个方向最多自动修正一次。只修改标题层，不重绘已合格的证书底图，也不改变用户原始标题。

严格按下列顺序选择第一个能解决当前问题的动作：

1. 若报告出现 `template_geometry_lost`、`template_material_mismatch` 或 `unwanted_gradient`，优先恢复 `Template DNA.title_system`：无字原生承载物、弧度、主副层、纯色填充/描边与阴影开关；禁止降级为通用直排或默认金色渐变；
2. 调整字距与行距；
3. 调整主副行字号比例；
4. 在同角色候选中选择覆盖完整字符的兼容字体；用户明确指定字体缺字时暂停，不得替换；
5. 恢复语义双行，`CERTIFICATE OF COMPLETION` 必须为 `CERTIFICATE` / `OF COMPLETION`，或同义的弧形/双飘带结构；
6. 降级为同设计家族的更稳定布局。

修正后重新运行标题专项验收。若仍未达到 85 分或仍有 hard failure，记录 `blocked` 并请用户决定，不得进行第二次自动修正。
