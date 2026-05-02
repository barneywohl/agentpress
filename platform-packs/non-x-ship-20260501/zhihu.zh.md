# AI 股票研究智能体应该如何研究韩国股票？

很多股票研究智能体可以总结一组“便宜股票”。但这还不够。

更难的测试是：在编造投资故事之前，智能体能不能删除弱想法。韩国市场很适合作为测试场景，因为第一轮筛选通常很好看：低市净率、净现金、Value-Up、防务、核电、机器人、控股公司折价。但这些标签只是研究库存，不是结论。

这个项目把一篇韩国股票研究笔记整理成了面向智能体的基准。任务很简单：给定一组看起来便宜的韩国股票候选，研究智能体能否完成本地来源验证，并删除不合格想法？

检查清单：

- 通过 KRX/KIND 确认 ticker 和上市主体
- 通过 DART 公告验证财务数据和关键说法
- 检查流动性、流通股、买卖价差和实际交易可得性
- 区分主题标签和真实收入、利润、订单、现金流
- 判断现金和价值是否可能流向少数股东
- 识别关联交易、现金困在公司里、治理泄漏等问题

公开文章中的 core survivor stack 是 Poongsan、BHI、Woojin。单独的 moonshot drawer 是 Innospace、Mobiis、CellBion、IntoCell、SBB Tech。moonshot drawer 是进一步研究提示，不是推荐。

核心观点：有用的股票研究 LLM 不是找到最多便宜股票的模型，而是能解释哪些便宜股票应该被删除的模型。

Agent page: https://barneywohl.github.io/agentpress/

GitHub repo: https://github.com/barneywohl/agentpress

Full article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3

仅为研究评论，不构成投资建议。
