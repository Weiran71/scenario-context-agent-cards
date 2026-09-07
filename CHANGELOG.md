# Changelog

## Unreleased

- 建立与内部项目隔离的公开研究原型目录。
- 增加事件提醒卡、POI 推荐卡的合成数据、生成基线和校验器。
- 增加公开方法、Schema、责任使用说明和完整运行示例。
- 扩充 README：补充问题定义、用户价值、核心亮点、两类卡片完整生产流程、输出契约、评测方式和限制说明。
- Hugging Face Dataset 已发布四配置（正/负向 × 两类卡片）；因免费账号不提供 Gradio 计算资源，Space 改为浏览器端 Static Demo，支持调整时间、天气和偏好并保持合成数据与权利声明边界。
- Hugging Face Dataset 与 Static Space 已完成公开发布和在线验证；README 与资产总览补充正式链接。
- Static Demo 增加运行状态反馈：点击“运行 Case”后显示最近运行的 Case 与时间，避免输入未变化时用户误以为按钮无响应。
- 新增《技术报告母稿》：完整说明 Context、情景与需求翻译、事件提醒卡、POI 推荐卡、服务决策、正负向数据集、Taste/Rubric、Demo 和公开边界，并明确方法目标与当前透明基线的差异。
