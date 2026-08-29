# 程序标题模式：无文字底图 Prompt

当 `title_treatment.render_mode` 为 `vector_flat` 或 `vector_effect` 时，把本段加入当前横版、竖版、模板转换或修改 Prompt：

> 本轮只生成证书画面底图。标题将在尺寸规格化后由程序绘制，因此标题核心区不得出现标题占位符、伪文字、字母、数字或符号串。默认不得生成横幅、丝带、卡片、徽章、文字底板或封闭标题容器；但当 Template DNA 的 `title_system.container=source_native` 时，必须保留或重建该模板独有的**无字**标题承载物（例如弧形双飘带、徽章或手绘底座），并保留其曲线、配色和材质，不能用通用容器替代。除标题区留空/无字承载物外，仍保持边框、插画、角色、配色和视觉重心完整。最终底图不得包含任何可读或疑似文字。

底图生成后先进行文字残留检查。只有确认全图无可读或疑似文字时，才可运行 `scripts/finalize_certificate.py` 并传入 `--base-text-free`。

`ai_integrated` 不使用本 Prompt，继续由生成模型完成唯一标题。
