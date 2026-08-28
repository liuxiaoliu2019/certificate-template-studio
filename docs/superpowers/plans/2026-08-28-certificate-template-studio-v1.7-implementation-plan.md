# Certificate Template Studio v1.7.0 实施计划

- 日期：2026-08-28
- 对应规格：`docs/superpowers/specs/2026-08-28-certificate-template-studio-v1.7-design.md`
- 基线提交：`5580b6c`
- 目标：在不降低质量门的前提下，实现质量托管、标题设计、严格状态机、缓存和低干预工作流

## 实施原则

- 每个任务先增加失败测试，再实现最小功能使测试通过。
- 每个阶段使用独立、可回退的 Git 提交。
- 不覆盖用户项目、现有 revision、批准记录或字体文件。
- 教材模式和模板模式复用公共状态、审批、Schema、路径和哈希逻辑。
- 不在同一个任务里同时重构脚本、修改 Prompt 和升级公开文档。
- 每完成一个阶段运行相关测试；发布前运行完整验证矩阵。
- 本计划不包含推送 GitHub、创建 Release 或安装到正式 Skill 目录；这些动作完成本地验收后单独授权。

## 阶段 0：建立 v1.7 回归测试基线

### 任务 0.1：创建测试目录和公共夹具

新增：

- `tests/conftest.py`
- `tests/fixtures.py`
- `tests/test_current_regressions.py`
- `pytest.ini`

修改：

- `requirements-dev.txt`
- `.github/workflows/validate.yml`

实现内容：

- 使用临时目录生成横竖空白图片、项目 manifest、Style Profile 和收尾报告。
- 统一定位 Windows、Linux 和 macOS 测试字体；测试夹具找不到字体时只跳过渲染用例，不跳过状态和审批用例。
- 将现有公开验证中的大型冒烟逻辑拆出可复用夹具，公开验证继续作为发布总入口。

先写回归测试，并以带缺陷编号的 `xfail(strict=True)` 标记当前已知失败：

- 仅空格标题当前会被接受。
- “不要确认横版定稿”当前会被接受。
- 收尾报告标题与 manifest 标题不一致当前可批准。
- 未分析、未输入标题可直接进入 `landscape_generated`。
- 横版批准后修订仍保留旧 `finalization_report`。
- 回退目标文件缺失时仍可登记回退。

验证：

```text
python -m pytest tests/test_current_regressions.py -q
```

初始预期：测试套件整体通过，并明确报告 6 个预期失败。后续修复对应缺陷时，同一提交移除该用例的 `xfail` 标记并确保测试通过，任何中间提交都不保留红色测试状态。

提交：

```text
test: capture v1.6 workflow regressions
```

## 阶段 1：公共运行时验证层

### 任务 1.1：集中 Schema 读取与验证

新增：

- `scripts/schema_runtime.py`
- `tests/test_schema_runtime.py`
- `requirements.txt`

修改：

- `scripts/_common.py`
- `requirements-dev.txt`

实现内容：

- 建立 Draft 2020-12 registry，一次加载 `schemas/*.schema.json`。
- 提供 `validate_document(instance, schema_name)`。
- 提供写入前、写入后的统一验证入口。
- 错误信息包含 JSON 路径、Schema 路径和失败原因。
- 运行时依赖与开发依赖分开：Pillow 与 jsonschema 进入 `requirements.txt`；pytest 和 PyYAML 保留在 `requirements-dev.txt`，开发依赖引用运行依赖。

测试：

- 合法示例通过。
- 缺必填字段、未知字段、错误枚举和交叉 `$ref` 明确失败。
- 错误输出不包含用户图片内容或本机敏感路径以外的无关数据。

提交：

```text
feat: add runtime schema validation
```

### 任务 1.2：集中项目路径、哈希和原子写入

新增：

- `scripts/project_io.py`
- `tests/test_project_io.py`

修改：

- `scripts/_common.py`

实现内容：

- 项目内相对路径解析统一拒绝越界、空路径和项目外输出。
- JSON 使用同目录临时文件、刷新并原子替换。
- 图片和报告使用临时路径，全部验证后再进入正式路径。
- 公共 SHA-256、时间戳和来源记录从重复脚本中移入该模块。

测试：

- `../`、绝对项目外路径和符号链接越界被拒绝。
- 写入验证失败时旧文件保持不变。
- 同名正式文件默认不覆盖。

提交：

```text
refactor: centralize project file safety
```

## 阶段 2：规范化状态机与智能入口

### 任务 2.1：实现唯一状态机

新增：

- `scripts/workflow_engine.py`
- `schemas/workflow_event.schema.json`
- `tests/test_workflow_engine.py`

修改：

- `schemas/project_manifest.schema.json`
- `schemas/template_project_manifest.schema.json`
- `scripts/init_project.py`
- `scripts/init_template_project.py`

版本升级：

- 教材 manifest：`1.5`
- 模板 manifest：`1.3`

实现内容：

- 分别定义教材和模板模式的有限状态集合与允许转移表。
- 每个动作声明来源阶段、必需文件、失效范围和目标阶段。
- 删除新项目中的历史同义阶段；旧阶段只由迁移器读取。
- `transition()` 在变更前验证前置条件，在变更后验证 manifest。
- 非审批操作不能进入批准阶段或 `complete`。

测试：

- 穷举所有合法转移。
- 穷举关键非法跳转。
- 未有 Style DNA、角色档案或标题不能规划横版。
- 横版未批准不能生成或批准竖版。
- 模板源方向未批准不能派生另一方向。

提交：

```text
feat: enforce canonical workflow states
```

### 任务 2.2：实现智能模式路由

新增：

- `references/start-routing-rules.md`
- `tests/test_start_routing.py`

修改：

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/quick_validate.py`

实现内容：

- 仅“开始工作”时保持固定两项菜单。
- 明确模式 1 或教材封面意图时直接锁定 `textbook_cover`。
- 明确模式 2 或模板双向意图时直接锁定 `template_bidirectional`。
- 同一消息的图片和标题直接接收。
- 意图不明确时必须显示菜单，不根据图片外观猜测。

测试：

- 通用启动返回固定菜单且只出现一次。
- 明确模式不重复菜单。
- 模糊表达不自动选模式。
- 已锁定项目中的“继续”恢复状态，不重新显示菜单。

提交：

```text
feat: add smart workflow routing
```

## 阶段 3：审批证据链与可靠修订

### 任务 3.1：统一收尾报告校验

新增：

- `scripts/approval_engine.py`
- `tests/test_approval_engine.py`

修改：

- `schemas/finalization_report.schema.json`
- `schemas/project_manifest.schema.json`
- `schemas/template_project_manifest.schema.json`
- `scripts/update_manifest.py`
- `scripts/update_template_manifest.py`
- `scripts/finalize_certificate.py`

实现内容：

- 报告必须包含 `ratio_error_percent`。
- 报告标题必须等于规范化后的 `manifest.current_title`。
- 报告方向、尺寸、格式、成品路径和哈希必须匹配。
- 报告标题模式必须匹配已批准 Style Profile 和标题布局计划。
- `ai_integrated` 必须引用质量报告路径和图片哈希，不再接受自声明布尔值。
- 教材和模板审批共用同一验证函数。

测试：

- 标题、方向、路径、哈希、模式、Profile 或布局计划任一不匹配均拒绝。
- 旧报告绑定新图片必须拒绝。
- 合法横竖报告可分别批准。

提交：

```text
fix: bind approvals to verified artifacts
```

### 任务 3.2：严格审批语义

新增：

- `tests/test_approval_language.py`

修改：

- `scripts/approval_engine.py`
- `references/revision-levels-and-state-lock.md`

实现内容：

- 先识别否定、未完成、条件式和疑问式，再识别肯定式审批。
- 明确绑定方向和当前显示成品 ID。
- `第一个可以`、`不错`、`继续`只作为选择或反馈。
- 审批事件记录用户原话、规范化意图、标题、方向、成品哈希、报告哈希、Profile 和布局计划。

测试：

- 覆盖已确认的肯定与否定中文短句。
- 否定词位于关键词前后都必须拒绝。
- 横版审批不能误批竖版，反之亦然。

提交：

```text
fix: reject ambiguous approval language
```

### 任务 3.3：修订、失效与哈希回退

新增：

- `scripts/revision_engine.py`
- `tests/test_revision_engine.py`

修改：

- `schemas/revision_log.schema.json`
- `scripts/record_revision.py`
- `scripts/record_template_revision.py`
- `scripts/update_manifest.py`
- `scripts/update_template_manifest.py`

实现内容：

- 教材和模板修订共用失效规则。
- 当前方向修订清除其批准状态、Master 和收尾报告。
- 横版修订使竖版状态、Master、报告失效；竖版修订不影响横版。
- 旧审批事件标记为历史，保留审计记录。
- 回退验证目标文件存在且哈希匹配。
- 回退后必须重新收尾和重新审批。

测试：

- 覆盖 LEVEL1/2/3 锁定范围。
- 覆盖横版到竖版的失效传播。
- 目标文件被删除或改写时回退拒绝。
- 历史文件不被覆盖或删除。

提交：

```text
fix: make revisions invalidate stale evidence
```

## 阶段 4：标题规划引擎

### 任务 4.1：定义标题布局 Schema 和语义规划器

新增：

- `schemas/title_layout_plan.schema.json`
- `scripts/title_planner.py`
- `tests/test_title_planner.py`
- `references/title-design-system.md`

修改：

- `schemas/certificate_style_profile.schema.json`
- `schemas/generation_config.schema.json`
- `references/v3-title-rules.md`

实现内容：

- 支持六类布局：正式双层、现代双层、典礼弧形、双层丝带、儿童趣味字、插画融合。
- 计划记录原文、规范化文本、语言、语义行、字体角色、字号比例、字距、行距、路径、容器、方向和位置。
- 横版宽度范围 52%–68%，竖版 58%–72%。
- 标题外接框 x=50%；竖版记录约 110 px 上移。
- 唯一主标题允许计划声明的丝带或装饰底座；其他文字容器继续禁止。

测试：

- `CERTIFICATE OF COMPLETION` 只允许正确双行、弧形或双层丝带。
- `CERTIFICATE OF / COMPLETION` 与单行直排失败。
- 中文固定词组、英文介词短语和中英混合标题语义分行正确。
- 计划生成可复现且符合 Schema。

提交：

```text
feat: add semantic title layout planning
```

### 任务 4.2：建立字体清单与字符覆盖

新增：

- `assets/fonts/README.md`
- `assets/fonts/font_manifest.json`
- `scripts/font_registry.py`
- `tests/test_font_registry.py`

修改：

- `LICENSE-ASSETS.md`
- `NOTICE.md`
- `requirements.txt`
- `scripts/public_release_validate.py`
- `scripts/build_release.py`

实现内容：

- 选择并固定四种可公开再分发的 OFL 字体角色：正式中英衬线、现代中英无衬线、英文典礼展示、儿童圆体。
- 优先级为用户项目字体、内置字体、明确系统回退。
- 使用 fontTools 字体表检查全部标题字符，不允许静默缺字；fontTools 作为运行依赖写入 `requirements.txt`。
- 用户商业字体只登记到项目，公开验证拒绝其进入 Skill 仓库。
- 字体 manifest 记录文件、角色、版本、来源、许可证和哈希。

测试：

- 中英文常用标题覆盖通过。
- 缺字字体明确失败。
- 用户指定字体优先。
- 公共发布只允许字体 manifest 中列出的字体文件。

提交：

```text
feat: bundle licensed title fonts
```

## 阶段 5：标题渲染与专项质量门

### 任务 5.1：重构确定性标题渲染器

新增：

- `scripts/title_renderer.py`
- `tests/test_title_renderer.py`

修改：

- `scripts/finalize_certificate.py`

实现内容：

- finalizer 只负责尺寸、合成、验证和报告；标题渲染下沉独立模块。
- 支持字体组合、主副行层级、显式字距、行距、逐字颜色和基线。
- 支持程序弧形文字、单层或双层丝带、确定性描边、阴影、渐变和金属效果。
- `vector_flat` 保持单色、无噪点、无随机纹理。
- 所有效果不使用随机数；相同参数输出哈希一致。
- 生成前检查 glyph，生成后计算标题外接框和中心误差。

测试：

- 六类布局至少各有一个渲染夹具。
- 横竖中心误差不超过 1 px。
- 竖版位移与计划一致。
- 扁平模式保持足够纯色像素。
- 效果模式重复渲染哈希一致。
- 丝带只含唯一标题，不创建其他文字区域。

提交：

```text
feat: render structured certificate titles
```

### 任务 5.2：标题专项评分与修正路由

新增：

- `schemas/title_quality_report.schema.json`
- `prompts/review-title-quality.md`
- `prompts/repair-title-layout.md`
- `scripts/title_quality.py`
- `tests/test_title_quality.py`

修改：

- `references/test-and-scoring.md`
- `references/output-and-title-rendering.md`

实现内容：

- 评分：字体匹配 20、层级 20、设计感 20、平衡 15、可读性 15、横竖一致性 10。
- 低于 85 分不得提交。
- 硬失败覆盖错字、缺字、错误分行、中心偏移、低对比、容器碰撞和扁平噪点。
- 修正顺序固定为字距与行距、字号比例、兼容字体、语义双行、同家族布局降级。
- 每方向最多自动修正一次。

测试：

- 分项总和与总分一致。
- `qualified` 与门槛一致。
- 硬失败覆盖普通分数。
- 第二次修正请求被拒绝并进入 `blocked`。

提交：

```text
feat: validate and repair title quality
```

## 阶段 6：项目缓存、Context Router 与 Metrics

### 任务 6.1：来源指纹和依赖失效

新增：

- `schemas/source_fingerprint.schema.json`
- `scripts/cache_engine.py`
- `tests/test_cache_engine.py`

修改：

- `scripts/init_project.py`
- `scripts/init_template_project.py`
- `scripts/extract_character_refs.py`
- `schemas/character_identity.schema.json`

实现内容：

- 记录来源、控制图和角色裁切哈希。
- 定义来源 → 分析 → Profile → 候选 → Master → 派生的依赖图。
- 标题变化只失效标题计划、标题渲染和报告。
- 角色变化只失效实际使用该角色的候选及其下游。
- 缓存命中不重复分析或生成。

测试：

- 相同来源重复运行命中缓存。
- 修改标题不失效主体分析。
- 修改封面使全部下游失效。
- 修改控制图只使对应方向及下游失效。

提交：

```text
feat: add dependency-aware project cache
```

### 任务 6.2：阶段上下文路由

新增：

- `schemas/active_context.schema.json`
- `references/context-routing.md`
- `scripts/context_router.py`
- `tests/test_context_router.py`

修改：

- `SKILL.md`
- 各阶段 `prompts/*.md`

实现内容：

- 定义分析、规划、横版、局部修改、竖版、多标题和审批七种上下文包。
- 每个包固定允许的 reference、prompt、JSON、图片类型和文本体积上限。
- 局部修改只包含当前图片、反馈、活动 Profile、布局计划、实际角色和锁定项。
- `active_context.json` 不复制完整历史和文档。

测试：

- 每个阶段只路由允许资源。
- 模式资料不交叉加载。
- 不使用角色的候选不加载角色裁切。
- 超过文本预算或包含禁止资源时失败。

提交：

```text
feat: route minimal stage context
```

### 任务 6.3：执行指标

新增：

- `schemas/execution_metrics.schema.json`
- `scripts/metrics.py`
- `tests/test_metrics.py`

修改：

- 初始化脚本、Context Router、缓存、生成和验收入口。

实现内容：

- 记录分析、规划、图片生成、视觉验收、自动修正、缓存命中、引用加载、Prompt 字符、图片输入和用户暂停。
- 宿主提供真实 Token 时记录可选字段，不把缺失 Token 当错误。
- Metrics 只记录计数和路径，不保存用户图片内容或完整 Prompt。

测试：

- 缓存命中和调用计数准确。
- 每方向自动修正上限可由 Metrics 验证。
- 多标题路径不会增加来源分析和三方案生成计数。

提交：

```text
feat: track workflow efficiency metrics
```

## 阶段 7：质量托管与最少干预交互

### 任务 7.1：统一质量报告和候选自动选择

新增：

- `schemas/quality_report.schema.json`
- `prompts/review-certificate-candidates.md`
- `scripts/quality_gate.py`
- `tests/test_quality_gate.py`

修改：

- `references/test-and-scoring.md`
- `prompts/landscape-three-concepts.md`
- `prompts/portrait-derivative.md`

实现内容：

- 三套横版一次性结构化验收。
- 角色硬门优先于普通评分。
- 自动选择最高分合格候选。
- 75–84 分只修正最高分候选一次；全部低于 75 分只重生成最有潜力方向一次。
- 保存全部候选和报告，默认只向用户提交最佳方案。
- 用户“查看其他方案”时返回其余合格候选。

测试：

- 有 85+ 候选时不修正低分候选。
- 最高分 75–84 只修正一次。
- 全部低分只触发一次重生成。
- 硬失败候选不能因总分高被选中。
- 默认对话摘要不包含完整内部分析。

提交：

```text
feat: add quality-managed candidate selection
```

### 任务 7.2：角色身份报告接入质量门

新增：

- `schemas/character_identity_report.schema.json`
- `prompts/review-character-identity.md`
- `tests/test_character_identity_gate.py`

修改：

- `schemas/character_identity.schema.json`
- `references/character-identity-lock.md`
- `scripts/quality_gate.py`

实现内容：

- 身份报告绑定角色 ID、来源裁切哈希、候选哈希和不可改变特征结果。
- 低于 85 分或任一不可改变项失败即硬失败。
- 角色来源不足时进入 `blocked` 并只询问更清晰图片。

测试：

- 错发型、脸部、服装分区、配件、物种或比例均失败。
- 姿势、朝向和媒介改变本身不失败。
- 不使用角色的候选不要求角色报告。

提交：

```text
feat: enforce character identity evidence
```

## 阶段 8：多标题派生和旧项目迁移

### 任务 8.1：实现横竖多标题快速通道

新增：

- `schemas/derivative_manifest.schema.json`
- `scripts/derive_title.py`
- `tests/test_title_derivatives.py`

修改：

- `references/multi-title-rules.md`
- `prompts/multi-title-derivative.md`
- `scripts/update_manifest.py`
- `scripts/update_template_manifest.py`

实现内容：

- 为新标题建立独立横竖布局计划、输出、报告和 derivative manifest。
- 不改变原 Master 的标题、图片、审批和哈希。
- 复用无文字底图；AI 融合 Master 只有具备安全标题区资产时才能快速派生，否则明确进入有限局部重生成。
- 新标题可在已批准标题家族内选择兼容布局变体。
- 用户明确重新探索风格时才退出快速通道。

测试：

- 多标题不增加 Style DNA 和三方案生成计数。
- 原 Master 文件和 manifest 保持不变。
- 横竖派生都达到固定尺寸并绑定新标题。
- 重复标题 slug 不覆盖旧派生。

提交：

```text
feat: implement dual-master title derivatives
```

### 任务 8.2：实现 v1.6 项目迁移

新增：

- `scripts/migrate_project.py`
- `schemas/migration_log.schema.json`
- `tests/test_project_migration.py`

修改：

- `references/revision-levels-and-state-lock.md`
- `README.md`
- `README.en.md`

实现内容：

- 识别教材 1.0–1.4 和模板 1.0–1.2 manifest。
- 迁移前建立项目内版本化备份。
- 映射旧阶段到新状态机。
- 缺完整报告的旧 Master 标记 `legacy_unverified`。
- 迁移重复运行保持幂等。

测试：

- 使用每个受支持旧版本夹具迁移。
- 迁移失败不修改原项目。
- 备份、迁移日志和哈希齐全。
- 已迁移项目再次运行不重复迁移。

提交：

```text
feat: migrate legacy certificate projects
```

## 阶段 9：Prompt、Reference、示例和入口收敛

### 任务 9.1：消除规则冲突并精简 SKILL.md

修改：

- `SKILL.md`
- `references/v3-title-rules.md`
- `references/output-and-title-rendering.md`
- `references/template-bidirectional-workflow.md`
- `references/multi-title-rules.md`
- `references/revision-levels-and-state-lock.md`
- 相关 `prompts/*.md`

实现内容：

- 版本升为 `1.7.0`。
- SKILL.md 只保留智能入口、Context Router、状态机、硬门和停止条件。
- 详细标题、质量、迁移、缓存和多标题规则按阶段读取。
- 将 `title_container_allowed` 与 `non_title_container_forbidden` 明确分离。
- 默认质量托管，只提交最佳候选；保留查看其他方案入口。
- 默认每方向自动修正一次。

测试：

- 引用链接全部存在。
- 不再同时出现“允许标题丝带”和“所有丝带禁止”的冲突。
- 固定输出、角色身份、唯一标题和审批硬门仍可被 quick validator 检测。

提交：

```text
docs: align v1.7 workflow instructions
```

### 任务 9.2：升级匿名化示例

新增或修改：

- `examples/SunnyFarmCourse/`
- `examples/TemplateBidirectional/`
- `examples/TitleLayouts/`

实现内容：

- 教材示例升级到 manifest 1.5。
- 模板示例升级到 manifest 1.3。
- 增加 source fingerprint、active context、title layout、quality report、metrics 和 derivative manifest 示例。
- 使用虚构标题和 `*-not-included.*` 占位，不加入教材或生成图片。

测试：

- 所有示例通过对应 Schema。
- 示例跨文件哈希字段使用明确的虚构占位策略或合法测试资产，不引用不存在的真实用户内容。

提交：

```text
docs: add v1.7 workflow examples
```

## 阶段 10：验证、安装和发布收尾

### 任务 10.1：升级快速和公开发布验证

修改：

- `scripts/quick_validate.py`
- `scripts/public_release_validate.py`
- `.github/workflows/validate.yml`

实现内容：

- quick validator 检查 v1.7 文件、状态、标题、缓存和质量不变量。
- public validator 运行 pytest、Schema、字体许可证、安装器、构建包和两模式完整冒烟。
- 新增审批绕过、标题错配、空标题、状态跳跃、旧报告、缓存和多标题回归用例。
- CI 继续覆盖 Windows、Ubuntu、Python 3.10 和 3.12。

验证：

```text
python -m pytest -q
python scripts/quick_validate.py .
python scripts/public_release_validate.py .
```

提交：

```text
test: validate v1.7 end-to-end workflow
```

### 任务 10.2：更新安装、打包和公开文档

修改：

- `README.md`
- `README.en.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `NOTICE.md`
- `LICENSE-ASSETS.md`
- `install.ps1`
- `install.sh`
- `scripts/build_release.py`
- `agents/openai.yaml`

实现内容：

- 文档说明智能入口、质量托管、标题布局、多标题快速通道和迁移。
- 安装器包含运行依赖说明、字体和新增目录。
- 强制安装后运行 quick validator。
- 构建包保持可复现，公开验证拒绝用户字体和私有内容。
- CHANGELOG 记录兼容和迁移边界。

验证：

- Windows 临时目录安装通过。
- Unix 临时目录安装通过。
- 两次构建 ZIP 哈希一致。
- 安装包中无 `.git`、缓存、用户图片、项目输出或未登记字体。

提交：

```text
docs: prepare v1.7 public release
```

## 阶段 11：最终本地验收

### 任务 11.1：全量验证和差异审查

只读检查：

```text
python -m pytest -q
python scripts/quick_validate.py .
python scripts/public_release_validate.py .
python scripts/build_release.py .
git diff v1.6.0...HEAD --check
git status --short
```

人工验收清单：

- 智能菜单和恢复流程符合最少交互目标。
- 三套横版后台评估，默认只提交最佳方案。
- 每方向最多自动修正一次。
- 六种标题布局可运行。
- `CERTIFICATE OF COMPLETION` 规则通过。
- 否定审批、空标题、报告错配和状态跳跃全部被拒绝。
- 修订、回退、多标题和迁移不覆盖历史。
- 横竖版尺寸和中心位置符合合同。
- 缓存与 Metrics 证明无重复分析。

提交：

```text
chore: finalize v1.7 validation
```

### 任务 11.2：等待发布授权

向用户提交：

- 本地版本号和提交范围；
- 完整验证结果；
- 发布 ZIP 路径和 SHA-256；
- 安装更新说明；
- 是否需要推送 GitHub、创建 `v1.7.0` tag/Release、安装到正式 Skill 目录的三个独立选项。

未经用户明确授权，不执行推送、Release 或正式安装。

## 推荐执行顺序与检查点

1. 阶段 0–3：先封住状态和审批漏洞。
2. 阶段 4–5：完成标题规划、字体和渲染闭环。
3. 阶段 6–7：接入缓存、Context Router、Metrics 和质量托管。
4. 阶段 8：完成多标题和旧项目迁移。
5. 阶段 9–10：统一 Skill 指令、示例和公开发布。
6. 阶段 11：全量本地验收并等待外部发布授权。

每个检查点结束时都必须保持测试通过和工作树可解释；若某阶段需要改变已批准规格，先更新规格并重新取得用户确认。
