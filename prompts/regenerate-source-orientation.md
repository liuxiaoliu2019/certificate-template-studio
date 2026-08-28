# 同方向模板重制 Prompt

## 输入

- Image A：用户源模板 `{source_template}`
- Image B：同方向隐藏控制图 `{control_path}`
- Template DNA：`{template_dna}`
- 源方向：`{source_orientation}`
- 用户标题：`{certificate_title}`
- 标题处理：`{title_treatment}`
- 可选角色身份档案与裁切：`{character_identity_and_refs}`

## Prompt

根据 Image A 和 Template DNA，重制一套与源模板同方向的证书原始图。横版保持接近 2172:1536，竖版保持接近 1536:2172，并优先使用服务可提供的最高原生分辨率。Image B 只提供本方向 Z80/Z50/Z20/Z12/Z08 的隐藏软性区域秩序，不复制其灰阶、纹理、轮廓或形状。

这不是简单擦字。完整重建源模板的主辅色比例、外框/主装饰框/内框层级、纹样造型语言与重复节奏、线条粗细、角部强化、材质、正式度和非文字装饰身份。清除所有源文字及其背景痕迹，恢复干净的正文、姓名和落款安全区。不得擅自简化、换色或替换边框。

按 `title_treatment.render_mode` 处理标题。`ai_integrated` 只生成“{certificate_title}”并锁定 x=50%；`vector_flat` 或 `vector_effect` 全图不生成文字，标题由收尾脚本绘制。程序模式仍通过字体类别、颜色和效果参数继承源模板的典礼感。竖版标题使用 y 9%–18%，正式输出上移约 110 px。

禁止生成副标题、正文、姓名、日期、学校、签名、印章文字、Logo、水印或伪文字。模板含角色时对照原图裁切和身份档案保持角色身份。输出一套同方向成品，不生成另一方向。
