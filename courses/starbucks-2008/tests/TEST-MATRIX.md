# V1.2设计测试与代码测试对应表

| 设计测试 | 设计要求 | 代码测试/证据 | V1.2状态 |
|---|---|---|---|
| T1 资源账本守恒 | 回填V1.0资源记录，发现MOVE 003成本显示与余额差额冲突，不覆盖原始记录 | test_v1_0_fixture_replays_and_preserves_gaps；test_v1_0_json_fixture_matches_legacy_loader | 已覆盖；MOVE 004子行动价格缺口保留 |
| T2 收入/指数恒等式 | 只有共同基期指数才可相乘；基期不一致拒绝计算 | test_same_base_indices_only | 已覆盖指数基期护栏；收入指数104→104.4的原始基期定义仍属数据缺口 |
| T3 顾客交易分解 | 活跃顾客数与单客频率在同基期下分解交易量；不得把低频客群活跃人数下降称为永久流失 | test_t3_customer_transactions_decomposition；simulation-data.md分层勾稽表 | 部分覆盖；分层权重和低频顾客频率缺失，无法复算分层总体 |
| T4 证据限制 | 非随机20家门店分类不得外推为全美蚕食率或竞品因果贡献 | test_evidence_grade_does_not_claim_causality | 部分覆盖；引擎尚无门店样本外推API，当前通过证据等级护栏与文档限制 |
| T5 培训试点因果边界 | 12+12非随机试点、有经理主动性与排班混杂时，不得自动宣称培训因果效应 | test_evidence_grade_does_not_claim_causality；simulation-data.md试点基线表 | 部分覆盖；基线缺失已登记，尚无统计估计器 |
| T6 资源与执行独立 | CEO决策精力为0时，已授权项目仍可继续执行 | test_execution_queue_can_continue_when_decision_energy_is_zero | 已覆盖最小不变量；完整任务队列调度仍未实现 |
| T7 策略分支差异 | 同一V1.0初始状态、同一规则注册表和参数下，不同策略形成不同轨迹 | test_t7_two_strategy_paths_from_real_v1_initial_state；fixtures/t7-strategy-branch-trajectories.json | 已覆盖并公开两条状态轨迹；参数为课堂假设，非历史校准 |
| T8 NPC自主性 | 检查触发条件；触发与未触发均记录，不能按固定节拍强制事件 | test_trigger_audit_records_fired_and_silent | 已覆盖触发评估日志；完整NPC目标/权限/行动模型未实现 |
| T9 历史信息防泄漏 | 历史资料未公开前不得作为玩家已知信息 | 当前无对应代码测试 | 未实现，列为后续P0；V1.2不宣称关闭 |
| T10 可回放性 | 相同初始状态、规则参数和事件序列产生相同状态；重复事件/依赖错误拒绝 | test_t10_replay_same_inputs_same_result；test_parallel_events_have_deterministic_commit_order；test_duplicate_event_id_rejected；test_unresolved_dependency_rejected；test_rule_invocation_inputs_are_immutable | 已覆盖最小回放与排序 |

## 解释

- “已覆盖”只表示对应的最小代码不变量有测试，不代表完整商业模拟器已完成。
- “部分覆盖”表示已有护栏或档案修复，但尚无完整算法/自动化验收。
- T9仍未实现。V1.2必须如实保留该缺口，不得把历史时间线文档拆分误称为玩家信息发布门控。
- T7的差异来自不同事件输入在同一已登记规则和参数下的计算结果；这证明规则会响应策略，不证明参数在现实中准确。
