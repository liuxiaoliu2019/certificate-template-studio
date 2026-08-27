---
name: certificate-template-studio
description: 从教材封面创建带角色身份锁的证书，或把用户提供的任意横版/竖版证书模板高保真重制为横竖双 Master。适用于三方案探索、完整边框、方向重构、修订回退、审批和多标题复用。
metadata:
  version: "1.5.1"
---

# Certificate Template Studio

建立可回退、可审批、可复用的教材证书设计项目。成品默认只生成唯一主标题；姓名、正文、日期、学校、签名和印章留给后期叠加。

## 必须先执行的模式菜单

每次开始新的 Skill 工作或建立新项目时，无论用户是否已经上传图片、说明图片类型或写明期望模式，都只输出以下固定菜单：

```text
请选择工作模式：
1｜教材封面生成证书
2｜现成模板双向转换

请回复 1 或 2。
```

- 不得在菜单前后增加模式介绍、流程说明、推荐语、图片分析结果或其他问题。
- 用户明确回复 `1` 或 `2` 前，不分析图片、不创建项目、不询问标题、不读取模式专属 reference 或 prompt，也不生图。
- 回复不是明确的 `1` 或 `2` 时，原样重新显示固定菜单，不推断模式。
- 回复 `1` 后锁定 `selected_mode=textbook_cover`。若当前对话已有用户上传的教材封面，直接使用；否则只问：`请上传教材封面。`
- 回复 `2` 后锁定 `selected_mode=template_bidirectional`。若当前对话已有用户上传的现成证书模板，直接使用；否则只问：`请上传现成横版或竖版证书模板。`
- 模式锁定后，本项目后续步骤不重复显示菜单。只有用户明确要求重新开始、切换模式或建立新项目时，才再次显示菜单。
- 初始化项目时必须把已锁定模式写入 manifest 的 `selected_mode`。切换模式必须新建对应模式项目，不复用另一模式的分析、manifest 或候选图。

`textbook_cover` 执行“教材证书模式”。`template_bidirectional` 读取 [references/template-bidirectional-workflow.md](references/template-bidirectional-workflow.md)，执行“模板双向生成模式”；该模式不要求教材封面、教材 Style DNA 或三方案探索，先审批方向由源模板方向决定。

## 教材证书模式：开始前

1. 定位教材封面和已有项目。新项目用 `scripts/init_project.py` 初始化，不覆盖非空目录。
2. 新项目先分析封面并写入 `analysis/style_dna.json`；再按 [references/character-identity-lock.md](references/character-identity-lock.md) 建立 `analysis/character_identity.json` 和原图角色裁切，不要立即生图。
3. 若用户尚未给出标题，Style DNA 与角色身份档案完成后必须暂停，只问：`请输入本次证书标题：`。不要推荐标题或同时询问风格偏好。
4. 同教材已有已批准 Master 时，默认走多标题衍生；只有用户明确要求重新探索风格时才重新生成三套。

## 按阶段读取

- 分析封面：读取 [references/design-rules.md](references/design-rules.md)。
- 封面含人物或动物角色：读取 [references/character-identity-lock.md](references/character-identity-lock.md)。
- 推荐风格：读取 [references/certificate-style-library.md](references/certificate-style-library.md)、[references/style-compatibility-scoring.md](references/style-compatibility-scoring.md) 和 [references/style-parameter-rules.md](references/style-parameter-rules.md)。
- 任何生图或标题修改：读取 [references/v3-title-rules.md](references/v3-title-rules.md)。
- 生成或评估三套横版：读取 [references/test-and-scoring.md](references/test-and-scoring.md)。
- 选择、修改、确认或回退：读取 [references/revision-levels-and-state-lock.md](references/revision-levels-and-state-lock.md)。
- 已有 Master 或同教材换标题：读取 [references/multi-title-rules.md](references/multi-title-rules.md)。
- 需要了解本轮风格来源时，读取 [references/reference-image-findings.md](references/reference-image-findings.md)。
- 模板双向生成：读取 [references/template-bidirectional-workflow.md](references/template-bidirectional-workflow.md) 和 [references/v3-title-rules.md](references/v3-title-rules.md)。

JSON 输出必须符合 `schemas/` 中对应 schema。只加载当前阶段需要的 prompt 和 reference。

## 教材证书模式：标准工作流

### 1. 初始化、Style DNA 与角色身份

- 提取优先级固定为：`画风 > 核心元素 > 色彩 > 整体气质 > 原构图`。
- 记录可转译的核心元素，以及不得复制的教材标题、Logo、出版社、系列、版次、ISBN 和独特商业版式。
- 摄影、写实或混合媒介允许转成证书风格对应的插画媒介，但必须保持核心元素、色彩关系和气质可识别。
- 对全部可识别的人类与动物角色建立独立身份档案。角色可以改变姿势、动作、朝向和绘制媒介，但发型/头部、脸部、肤色或毛羽色、服装分区、标志性配件、物种与身体比例不得改变。
- 不要求每套使用全部角色；凡是出现的角色都必须输入完整封面、对应原图裁切和身份档案，并先通过身份一致性硬门。
- Style DNA 与角色身份档案结束后进入 `waiting_for_title`，不得直接推荐风格或生图。

### 2. 获取用户标题

- 标题只能来自用户手动输入；写入 manifest 后不重复确认。
- 唯一可读文字就是该标题。副标题、装饰字、伪文字和变量信息均视为失败。
- 横竖版标题外接框的水平中心固定为画布 `x=50%`。
- 竖版标题在 V3 基准位置上固定向上移动 `1.5 cm`。详见标题规则。

### 3. 推荐三种证书风格

- 标题确认后，使用 `prompts/recommend-certificate-styles.md` 对 7 个风格家族逐一评分。
- 权重固定为：画风 35、核心元素 25、色彩 20、整体气质 15、原构图可转化性 5；候选最低 70 分。
- 选择 3 个不同且合格的风格家族，为每个建立 `certificate_style_profile`。
- 任意两个 Profile 至少有 3 项核心参数不同。若差异检查失败，先重配方向，不要生图。
- 三套必须分别承担 `cover_character_led`、`balanced_translation`、`frame_led` 三个设计角色；默认第 3 套为 `frame_led + full_frame`。
- `frame_led` 以边框造型、纸张、线条、纹样和典礼秩序为主，教材只提供少量配色、年龄感或主题线索；允许不使用角色。边框是独立版式轴，不等同于某一个风格家族。
- 保存 `analysis/style_recommendation.json` 和三个 Profile，再进入横版生成。

### 4. 生成三套横版

- 每套输入教材封面、Style DNA、用户标题、项目内 `controls/landscape_v3.png` 和各自 Style Profile。含角色方案还必须输入实际使用角色的原图裁切和身份档案。
- 教材决定“画什么”；风格 Profile 决定“用什么证书语言表现”；控制图决定“放在哪里和区域密度”。
- 控制图是隐藏软约束，不复制灰阶、纹理、边界或形状，也不进入成品。
- 左右下角都必须有清晰视觉锚点；两侧以逐渐变小的图案、线条、环境或色彩形成弱连接。中部可稀疏，不能生硬断开或让一侧完全空白。
- 中央变量安全区和右下偏内侧落款区必须可排版；安静不等于零密度。
- 完整边框可沿 Z50 四边连续，在 Z80 四角增强；不得因控制图软约束被退化为零散角花。
- 含角色方案先进行身份验收：低于 85 分或任一不可改变项明显错误即硬失败，不进入普通百分制评分，也不得提交用户。
- 生成后评分。低于 75 分不得提交；75 至 84 分先自动修正；85 分以上才能提交用户选择。
- 输出三套后暂停，请用户选择 1/2/3 或提出自然语言修改。选择不是批准。

### 5. 修改、风格锁与回退

- LEVEL1：局部轻改，锁定风格家族、Profile 核心参数、主构图和标题原文。
- LEVEL2：同一风格家族内重组布局或参数，锁定风格身份、标题原文和中央功能区。
- LEVEL3：用户明确重做或换风格时解除风格锁，重新评分或建立新 Profile；旧版本保留。
- 只要修订后仍使用原角色，人物身份锁在 LEVEL1/2/3 均不可解除；更换风格不等于允许重设计角色。
- 每次修改用 `scripts/record_revision.py` 保存图片、反馈、等级、Style Profile、参数变化和锁定项，不覆盖旧文件。
- 回退只移动 active revision，保留全部历史。

### 6. 横版批准锁

- 只有用户对明确对象表达定稿意图，例如“确认横版定稿”“确认方案 2 为横版定稿”，才可批准横版。
- “第一个可以”“这个不错”“继续”“下一步”、只选择编号、要求继续修改或模型评分均不算批准。
- 横版未批准时竖版保持阻塞。

### 7. 竖版衍生

- 横版明确批准后，同时输入教材封面、Style DNA、已批准横版、已批准 Style Profile 和项目内 `controls/portrait_v3.png`。若批准横版含角色，同时输入对应身份档案和原图裁切。
- 继承风格家族和核心参数，按竖版控制图重新构图；禁止裁切、拉伸、旋转或机械搬运横版。
- 标题水平居中并向上 1.5 cm；继续保持左右锚点、边缘连接、中央安全区和落款功能区。
- 竖版也必须由用户明确表达“确认竖版定稿”后才能批准。

### 8. Master 与多标题

- 横版批准后记录 Master 横版与已批准 Style Profile；竖版批准后补充 Master 竖版并保存 `master_style_profile.json`。
- 同教材新标题默认只替换标题并进行必要的字号、字距、换行和少量联动装饰调整，不重新推荐风格。
- 用户明确要求“重新探索风格”时才建立新分支。

## 模板双向生成模式

1. 用 `scripts/init_template_project.py` 保存用户模板、自动识别横/竖方向并建立独立项目；正方形输入需由用户明确指定源方向。
2. 用 `prompts/analyze-certificate-template.md` 提取边框、纹样、配色、线宽、材质、非文字装饰、留白和文字区域，保存 `analysis/template_dna.json`。文字区域只记录位置和删除动作，不保存原文。
3. 若用户尚未给标题，暂停并只问：`请输入证书标题：`。用户已给标题时不重复询问。
4. 先用源模板、Template DNA、同方向控制图和 `prompts/regenerate-source-orientation.md` 重制一套同方向干净版本。删除全部源文字，只生成用户标题。
5. 同方向版本达到 85 分且无硬失败后提交用户。必须明确确认该方向定稿，另一方向才解除阻塞。
6. 用源模板、Template DNA、已批准同方向 Master、目标方向控制图和 `prompts/derive-opposite-orientation.md` 重新构图另一方向。禁止旋转、拉伸、压缩、裁切或直接扩边。
7. 横竖版标题外接框都锁定 x=50%；竖版另执行相对 V3 基准向上 1.5 cm。
8. 每个方向默认只生成一套，分别明确批准；两个方向都批准后保存横版与竖版 Master。
9. 后续新标题默认同时复用两个 Master，只适配标题，不重新分析或重构边框。

## 失败与停止条件

- 多余文字、标题错字、标题偏离水平中心、主体侵入功能区、单侧失重、控制图痕迹、复制教材文字或 Logo，均不得交付。
- 含角色成品发生身份漂移、角色混合、服装/毛羽色错误或标志性特征缺失时，不得交付；不得用“已改变画风”作为放宽理由。
- 自动修正最多连续两次。仍不合格时保留最好版本并说明问题，不无限重试。
- Schema、manifest、Profile 或脚本验证失败时停止生图。
- 当前环境没有图像生成能力时，可以完成分析、风格推荐、配置和 prompts，但必须明确说明图片尚未生成。
- 模板模式中若源文字残留、边框断裂、纹样被压扁、设计身份明显丢失，或跳过源方向批准，均不得交付。

## 辅助脚本

```text
python scripts/init_project.py --name SunnyFarmCourse --root <项目父目录> --cover <封面路径>
python scripts/update_manifest.py <项目目录> --set current_title='"英语之星"'
python scripts/record_revision.py <项目目录> --orientation landscape --level 1 --artifact <图片> --feedback "标题上移" --style-family S05_childrens_flat_education --profile styles/candidate-2.json
python scripts/update_manifest.py <项目目录> --approve-landscape selected/master_landscape.png --style-profile styles/approved.json --user-confirmation "确认横版定稿"
python scripts/quick_validate.py <Skill目录>
python scripts/init_template_project.py --name ClassicBlue --root <项目父目录> --template <横版或竖版模板路径>
python scripts/update_template_manifest.py <模板项目目录> --set-title "结业证书"
python scripts/update_template_manifest.py <模板项目目录> --approve-orientation landscape --artifact selected/master_landscape.png --user-confirmation "确认横版定稿"
```

脚本只执行确定性记录，不代替风格判断、视觉评分或用户审批。
