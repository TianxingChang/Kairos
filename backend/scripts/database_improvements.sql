-- 数据库改进脚本
-- 解决核心结构和数据质量问题

-- 1. 创建知识点和学习资源的关联表 (多对多关系)
CREATE TABLE IF NOT EXISTS ai.knowledge_resource_map (
    id SERIAL PRIMARY KEY,
    knowledge_id INTEGER NOT NULL REFERENCES ai.knowledge(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES ai.learning_resource(id) ON DELETE CASCADE,
    relevance_score DECIMAL(3,2) DEFAULT 1.0, -- 相关度评分 (0.0-1.0)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(knowledge_id, resource_id) -- 防止重复关联
);

-- 2. 标准化 difficulty_level 字段
-- 将所有非标准格式的difficulty_level统一为1-10的整数

-- 更新knowledge表中的difficulty_level
UPDATE ai.knowledge SET difficulty_level = '1' WHERE difficulty_level = 'beginner';
UPDATE ai.knowledge SET difficulty_level = '3' WHERE difficulty_level = 'intermediate';
UPDATE ai.knowledge SET difficulty_level = '5' WHERE difficulty_level = 'advanced';
UPDATE ai.knowledge SET difficulty_level = '2' WHERE difficulty_level = '2';
UPDATE ai.knowledge SET difficulty_level = '3' WHERE difficulty_level = '3';
UPDATE ai.knowledge SET difficulty_level = '5' WHERE difficulty_level = '5';
-- 为空值设置默认难度
UPDATE ai.knowledge SET difficulty_level = '3' WHERE difficulty_level IS NULL;

-- 更新learning_resource表中的difficulty_level
UPDATE ai.learning_resource SET difficulty_level = '1' WHERE difficulty_level = 'beginner';
UPDATE ai.learning_resource SET difficulty_level = '3' WHERE difficulty_level = 'intermediate';
UPDATE ai.learning_resource SET difficulty_level = '5' WHERE difficulty_level = 'advanced';
-- 为空值设置默认难度
UPDATE ai.learning_resource SET difficulty_level = '3' WHERE difficulty_level IS NULL;

-- 3. 统一domain领域分类
-- 建立层级化的领域分类
UPDATE ai.knowledge SET domain = '数学基础' WHERE domain = '数学';
UPDATE ai.knowledge SET domain = '人工智能' WHERE domain = '机器学习';
UPDATE ai.knowledge SET domain = '人工智能' WHERE domain = '深度学习';
UPDATE ai.knowledge SET domain = '人工智能' WHERE domain = '强化学习';
UPDATE ai.knowledge SET domain = '人工智能' WHERE domain = '生成式AI';
UPDATE ai.knowledge SET domain = '人工智能' WHERE domain = '計算機視覺';
UPDATE ai.knowledge SET domain = '人工智能' WHERE domain = '自然語言處理';

-- 统一使用简体中文
UPDATE ai.knowledge SET domain = '机器学习' WHERE domain = '機器學習';
UPDATE ai.knowledge SET domain = '深度学习' WHERE domain = '深度學習';
UPDATE ai.knowledge SET domain = '强化学习' WHERE domain = '深度強化學習';
UPDATE ai.knowledge SET domain = '计算机视觉' WHERE domain = '計算機視覺';
UPDATE ai.knowledge SET domain = '自然语言处理' WHERE domain = '自然語言處理';

-- 4. 统一language语言代码
UPDATE ai.learning_resource SET language = 'zh-CN' WHERE language IN ('zh', 'zh-TW');
UPDATE ai.learning_resource SET language = 'en-US' WHERE language = 'en';

-- 5. 修正明显的数据错误
-- 修正id=1的学习资源内容错误
UPDATE ai.learning_resource 
SET description = 'MIT线性代数公开课，由Gilbert Strang教授主讲，涵盖线性代数的核心概念包括矩阵运算、向量空间、特征值和特征向量等。',
    transcript = '本课程介绍线性代数的基本概念：矩阵和向量运算、线性方程组求解、向量空间和子空间、线性变换、特征值和特征向量、矩阵分解等核心内容。'
WHERE id = 1;

-- 6. 填充关键的缺失数据
-- 为knowledge表补充search_keywords
UPDATE ai.knowledge SET search_keywords = '线性代数,矩阵,向量,数学基础' WHERE id = 1 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '概率论,统计,随机变量,数学基础' WHERE id = 2 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'Python,编程,基础语法,数据结构' WHERE id = 3 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '机器学习,监督学习,无监督学习,算法' WHERE id = 4 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '神经网络,深度学习,反向传播,激活函数' WHERE id = 5 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '强化学习,智能体,环境,奖励' WHERE id = 6 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'PPO,策略优化,强化学习算法' WHERE id = 100 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'Q-Learning,值函数,强化学习' WHERE id = 101 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'DQN,深度Q网络,强化学习' WHERE id = 102 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '扩散模型,生成模型,去噪' WHERE id = 103 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'Transformer,注意力机制,编码器解码器' WHERE id = 104 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'CNN,卷积神经网络,图像识别' WHERE id = 105 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'RNN,循环神经网络,序列建模' WHERE id = 106 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '模型评估,交叉验证,性能指标' WHERE id = 107 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'GAN,生成对抗网络,生成模型' WHERE id = 108 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '强化学习环境,OpenAI Gym,仿真' WHERE id = 109 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'LSTM,长短期记忆,序列建模' WHERE id = 110 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '卷积层,特征提取,CNN架构' WHERE id = 111 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = '注意力机制,self-attention,Transformer' WHERE id = 112 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'VAE,变分自编码器,生成模型' WHERE id = 113 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'Actor-Critic,策略梯度,值函数' WHERE id = 114 AND search_keywords IS NULL;
UPDATE ai.knowledge SET search_keywords = 'DDPG,连续控制,强化学习' WHERE id = 115 AND search_keywords IS NULL;

-- 设置is_active为true (如果为NULL)
UPDATE ai.knowledge SET is_active = true WHERE is_active IS NULL;

-- 设置estimated_hours的合理默认值
UPDATE ai.knowledge SET estimated_hours = 8 WHERE id <= 6 AND estimated_hours IS NULL; -- 基础课程
UPDATE ai.knowledge SET estimated_hours = 4 WHERE id > 6 AND estimated_hours IS NULL; -- 高级主题

-- 7. 建立初始的知识点和学习资源关联关系
-- 基于合理推测建立关联
INSERT INTO ai.knowledge_resource_map (knowledge_id, resource_id, relevance_score) VALUES
(1, 1, 1.0), -- 线性代数基础 -> MIT线性代数公开课
(3, 2, 0.9), -- Python编程基础 -> Python官方文档
(4, 3, 0.8), -- 机器学习基础 -> 机器学习课程视频
(5, 4, 0.9), -- 神经网络基础 -> 深度学习课程
(104, 5, 1.0), -- Transformer架构 -> Transformer论文
(105, 6, 0.9), -- CNN -> CNN教程视频
(1, 7, 0.7), -- 线性代数基础 -> 线性代数PDF教程
(2, 8, 0.8), -- 概率论基础 -> 概率论讲义
(6, 9, 0.9), -- 强化学习基础 -> 强化学习入门
(104, 10, 0.8) -- Transformer -> Attention机制详解
ON CONFLICT (knowledge_id, resource_id) DO NOTHING;

-- 8. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_knowledge_resource_map_knowledge_id ON ai.knowledge_resource_map(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_resource_map_resource_id ON ai.knowledge_resource_map(resource_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON ai.knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_difficulty ON ai.knowledge(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_resource_type ON ai.learning_resource(resource_type);
CREATE INDEX IF NOT EXISTS idx_resource_language ON ai.learning_resource(language);

COMMIT;