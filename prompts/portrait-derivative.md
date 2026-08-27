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
- 唯一标题：`{certificate_title}`

## Prompt

基于三张参考输入，重新构图生成 A4 竖版证书背景图（2480 × 3508 px，300 DPI 版式感）。这不是横版裁切、拉伸、旋转或元素机械搬运。

Image A 与 Style DNA 提供核心元素、色彩和气质；已批准 Style Profile 提供风格家族与核心参数；Image C 提供已批准的系列身份；Image B 只提供竖版 Z80/Z50/Z20/Z12/Z08 的软性区域秩序，不复制灰阶、纹理、边界或形状。

继承 Style Profile 的风格家族和核心参数，为竖版重新安排主次关系。保持中央正文区干净；左右下角都要有可见锚点，并以由大到小的同风格元素建立弱连接。右下偏内侧落款/盖章功能区低对比、无主体且可排版。不得擅自更换风格家族。

若批准横版含教材角色，竖版仍必须对照完整封面、对应原图裁切与身份档案保持角色身份；只允许重新安排姿势、朝向、尺寸和位置。若批准 Profile 为 `frame_led + full_frame`，竖版应重新设计适合竖向节奏的四边连续完整边框，不得裁切或机械拉长横版边框。

在竖版标题核心区准确生成唯一标题“{certificate_title}”。完整标题外接框的几何中心必须严格锁定在画布水平中轴 x=50%。相对原 V3 文字核心区 x 24%–76%、y 14%–23%，将标题整体固定向上移动 1.5 cm，即 A4 竖版画布高度约 5.05%（3508 px 约 177 px）；移动后的文字核心区为 x 24%–76%、y 9%–18%，垂直中心建议约 y 13.5%。标题与横版属于同一视觉体系，不使用横幅、卡片、底板、徽章、边框或封闭容器。

除该标题外，禁止任何其他可读或疑似文字；不生成姓名、正文、日期、学校、签名或印章。输出完整竖版成品。
