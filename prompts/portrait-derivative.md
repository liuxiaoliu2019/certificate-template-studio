# 竖版衍生 Prompt

## 前置条件

只有 manifest 中 `landscape.status = approved`，且保存了用户明确批准原话时才可使用。

## 输入

- Image A：教材封面 `{cover_path}`
- Image B：项目内竖版隐藏控制图 `{project_dir}/controls/portrait_v3.png`
- Image C：已确认横版 `{approved_landscape_path}`
- Style DNA：`{style_dna}`
- 角色身份档案与批准方案所用角色裁切：`{character_identity_and_refs}`
- 已批准 Style Profile：`{approved_style_profile}`
- 已批准标题处理：`{title_treatment}`
- 唯一标题：`{certificate_title}`

## Prompt

基于三张参考输入，重新构图生成竖版证书原始图。保持接近 1536:2172 的比例并优先使用服务可提供的最高原生分辨率；正式尺寸由收尾脚本完成。这不是横版裁切、拉伸、旋转或元素机械搬运。

Image A 与 Style DNA 提供核心元素、色彩和气质；已批准 Style Profile 提供风格家族与核心参数；Image C 提供已批准的系列身份；Image B 只提供竖版 Z80/Z50/Z20/Z12/Z08 的软性区域秩序，不复制灰阶、纹理、边界或形状。

继承 Style Profile 的风格家族和核心参数，为竖版重新安排主次关系。保持中央正文区干净；左右下角都要有可见锚点，并以由大到小的同风格元素建立弱连接。右下偏内侧落款/盖章功能区低对比、无主体且可排版。不得擅自更换风格家族。

若批准横版含教材角色，竖版仍必须对照完整封面、对应原图裁切与身份档案保持角色身份；只允许重新安排姿势、朝向、尺寸和位置。若批准 Profile 为 `frame_led + full_frame`，竖版应重新设计适合竖向节奏的四边连续完整边框，不得裁切或机械拉长横版边框。

按 `title_treatment.render_mode` 处理标题。`ai_integrated` 在 x 24%–76%、y 9%–18% 准确生成唯一标题“{certificate_title}”，标题外接框中心锁定 x=50%；`vector_flat` 或 `vector_effect` 读取 `generate-title-free-base.md`，全图不生成文字，标题由收尾脚本在最终 1536×2172 画布上绘制。竖版标题相对原 V3 基准按画布高度 5.05% 上移，正式输出约 110 px。所有模式均不使用横幅、卡片、底板、徽章、边框或封闭标题容器。

最终成品除该标题外禁止任何其他可读或疑似文字；不生成姓名、正文、日期、学校、签名或印章。输出竖版原始图后必须收尾为 1536×2172 PNG。
# 质量托管补充

竖版完成后先执行角色身份、标题专项和整图质量门。未达到 85 分时只允许一次自动修正；通过后再提交用户确认，评分不能代替批准。
