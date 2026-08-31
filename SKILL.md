---
name: certificate-template-studio
description: 从教材封面创建带角色身份锁的横竖证书 Master，或把现成横版/竖版证书模板高保真双向重构；支持质量托管、标题设计、审批、回退和多标题复用。
metadata:
  version: "1.7.1"
---

# Certificate Template Studio

创建可验证、可回退、可复用的横竖证书。成品唯一可读文字是用户输入的主标题；姓名、正文、日期、学校、签名和印章由后期叠加。

## 启动路由

先按 [start-routing-rules.md](references/start-routing-rules.md) 路由，或运行 `scripts/start_router.py`。用户未明确模式时只输出：

```text
请选择工作模式：
1｜教材封面生成证书
2｜现成模板双向转换

请回复 1 或 2。
```

用户已明确模式时不重复菜单；同一消息中的模式、图片和标题一次接收。缺图片时只请求对应图片，缺标题时完成来源分析后只问：`请输入本次证书标题：`。已有项目按 manifest 恢复，不重复有效阶段。

## 最小上下文与缓存

每个动作先按 [context-routing.md](references/context-routing.md) 建立最小 `active_context.json`，不得加载完整历史、另一模式资料或未使用角色裁切。按 `configs/source_fingerprint.json` 和 `cache_state.json` 复用有效结果：改标题只失效标题层；改来源才失效全链路；改控制图只影响对应方向及下游。

## 模式 1｜教材封面

1. 用 `scripts/init_project.py` 初始化；读取 [design-rules.md](references/design-rules.md) 和 `prompts/analyze-cover.md`，按“画风 > 核心元素 > 色彩 > 整体气质 > 原构图”保存 Style DNA。
2. 封面含人物或动物时读取 [character-identity-lock.md](references/character-identity-lock.md)，建立身份档案和原图裁切。姿势、朝向、动作与媒介可变；头发/头部、脸部、服装或表面分区、配件、物种和比例不可变。
3. 标题确认后读取风格库与评分规则，内部建立三个不同的 Style Profile 和横版候选，其中至少一个为完整边框主导型。
4. 按 [test-and-scoring.md](references/test-and-scoring.md) 统一验收三套；默认只提交最高分且无硬失败的一套。用户要求“查看其他方案”时再展示其余合格候选。
5. 选择不等于批准。自然语言修改按 [revision-levels-and-state-lock.md](references/revision-levels-and-state-lock.md) 记录 LEVEL1/2/3 和历史。
6. 用户明确确认横版定稿后才生成竖版；同时输入封面、Style DNA、批准横版、批准 Profile、实际角色证据和竖版控制图，重新构图而非裁切或拉伸。

状态机由 `scripts/workflow_engine.py` 强制：

```text
initialized → analyzing_source → awaiting_title → planning_landscape
→ generating_landscape → validating_landscape → awaiting_landscape_approval
→ generating_portrait → validating_portrait → awaiting_portrait_approval → complete
```

修订、阻塞和多标题是受控分支，不能跳过批准门。

## 模式 2｜现成模板双向转换

读取 [template-bidirectional-workflow.md](references/template-bidirectional-workflow.md)，用 `scripts/init_template_project.py` 初始化。源模板决定边框、纹样、配色、线宽、材质、证书秩序和非文字标题结构；删除全部源文字，先重制并批准源方向，再按目标控制图重构另一方向。弧形/飘带标题的曲线、原生承载物、字体气质和扁平/效果材质必须由 `Template DNA.title_system` 锁定，不能被默认直排或金色渐变覆盖。程序标题调用 `title_planner.py --template-dna` 与 `finalize_certificate.py --template-dna`。禁止旋转、拉伸、机械裁切、直接扩边或复制纵横布局。

```text
initialized → analyzing_source → awaiting_title → regenerating_source
→ validating_source → awaiting_source_approval → deriving_opposite
→ validating_opposite → awaiting_opposite_approval → complete
```

## 标题与输出硬门

任何生图或标题修改读取 [v3-title-rules.md](references/v3-title-rules.md)、[title-design-system.md](references/title-design-system.md) 和 [output-and-title-rendering.md](references/output-and-title-rendering.md)。

- 横竖标题完整外接框水平中心固定 `x=50%`，误差不超过 1 px；竖版相对 V3 基准上移约 110 px（1.5 cm）。
- `CERTIFICATE OF COMPLETION` 必须为 `CERTIFICATE` / `OF COMPLETION` 两行，或等价浅弧/双飘带结构。
- 标题家族：正式双层、现代双层、典礼弧形、双层飘带、儿童逐字配色、插画融合底座。
- 丝带或底座只可服务唯一主标题；禁止姓名卡、正文卡、日期徽章、签名横幅等额外文字容器。
- `vector_flat` 保持纯色无噪点；`vector_effect` 使用确定性渐变、描边和阴影；`ai_integrated` 必须经过视觉文字验收。
- 模板模式的平面标题必须保留源模板规定的纯色和可选纯色描边；未被 `title_system` 明确允许时，渐变、金属高光和阴影均为硬失败。
- 正式横版为 `2172×1536` PNG，竖版为 `1536×2172` PNG。必须运行 `scripts/finalize_certificate.py` 并保存通过的收尾报告。

## 质量托管与停止条件

- 角色身份报告先于普通评分；低于 85、任一不可改变特征失败或来源不足均不得提交。
- 标题专项和整图评分都需至少 85 且无硬失败。每个方向最多自动修正一次；仍失败则暂停请用户决定。
- 错字、缺字、多余文字、标题偏心、尺寸错误、控制图痕迹、复制教材 Logo/文字、单侧失重、功能区侵入、边框断裂或审批证据不匹配均为硬失败。
- 当前环境没有图像生成能力时，只完成分析、配置与 Prompt，并明确说明图片尚未生成。

## 审批、多标题与迁移

只有针对明确文件的“确认横版定稿/确认竖版定稿”等肯定原话才构成批准；“可以、不错、继续、1/2/3”都不构成批准。批准必须绑定当前标题、方向、尺寸、成品哈希和收尾报告。

双 Master 批准后按 [multi-title-rules.md](references/multi-title-rules.md) 运行 `scripts/derive_title.py`；不重新分析来源或探索三套。用户明确要求重新探索风格时才退出快速通道。旧项目先运行 `scripts/migrate_project.py`；缺新版证据的旧 Master 标记 `legacy_unverified`。

JSON 必须符合 `schemas/`。脚本负责确定性状态、记录、验证与渲染，不代替用户批准。
