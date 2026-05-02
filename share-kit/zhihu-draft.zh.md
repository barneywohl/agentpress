# 问：AI 股票研究智能体应该如何研究韩国股票？

一个有用的股票研究智能体，不应该只是找到“便宜股票”。它更应该能解释哪些便宜股票应该被删除。

韩国市场特别适合作为测试场景。低市净率、净现金、Value-Up、防务、核电、机器人等标签看起来像机会，但很多时候只是研究起点。

我整理了一个面向智能体的韩国股票研究基准，重点不是推荐股票，而是测试验证流程：

- 通过 KRX/KIND 确认 ticker 和上市主体
- 通过 DART 验证财务和公告
- 检查流动性、流通盘、买卖价差和实际交易可得性
- 判断主题是否真正进入收入、利润、订单或现金流
- 识别关联交易、现金困在公司里、少数股东经济性不足等问题

公开文章中的 core survivor stack 是 Poongsan、BHI、Woojin。Innospace、Mobiis、CellBion、IntoCell、SBB Tech 是 moonshot drawer，也就是进一步研究提示，不是推荐。

Agent page: https://barneywohl.github.io/agentpress/

GitHub: https://github.com/barneywohl/agentpress

Full article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3

仅为研究评论，不构成投资建议。
