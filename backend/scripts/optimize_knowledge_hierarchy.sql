-- 知识表层级结构优化脚本
-- 目标：建立完整的L1 -> L2 -> L3 三级知识层级

BEGIN;

-- 1. 首先确保knowledge_level字段存在且有正确的默认值
ALTER TABLE ai.knowledge ALTER COLUMN knowledge_level TYPE VARCHAR(2);
ALTER TABLE ai.knowledge ALTER COLUMN knowledge_level SET DEFAULT 'L3';

-- 2. 为人工智能域添加L2层级知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id) VALUES 
('深度学习基础', '深度神经网络的基本概念、反向传播算法、激活函数等核心原理', '人工智能', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '神经网络基础' AND knowledge_level = 'L1' LIMIT 1)),
('计算机视觉', '图像处理、目标检测、图像分类等计算机视觉基础技术', '人工智能', 'L2', 4, 3,
 (SELECT id FROM ai.knowledge WHERE title = '机器学习基础' AND knowledge_level = 'L1' LIMIT 1)),
('自然语言处理', 'NLP基础技术、文本预处理、语言模型等核心概念', '人工智能', 'L2', 4, 3,
 (SELECT id FROM ai.knowledge WHERE title = '机器学习基础' AND knowledge_level = 'L1' LIMIT 1));

-- 3. 为强化学习域添加L2层级知识点  
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id) VALUES
('值函数方法', '基于值函数的强化学习方法，包括Q-learning和TD学习', '强化学习', 'L2', 3, 2,
 (SELECT id FROM ai.knowledge WHERE title = '强化学习环境' AND knowledge_level = 'L1' LIMIT 1)),
('策略梯度方法', '直接优化策略的强化学习方法，包括REINFORCE和Actor-Critic', '强化学习', 'L2', 4, 2,
 (SELECT id FROM ai.knowledge WHERE title = '强化学习环境' AND knowledge_level = 'L1' LIMIT 1));

-- 4. 为数学基础域添加L2层级知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id) VALUES
('矩阵运算', '矩阵乘法、特征值分解、奇异值分解等线性代数核心运算', '数学基础', 'L2', 2, 2,
 (SELECT id FROM ai.knowledge WHERE title = '线性代数基础' AND knowledge_level = 'L1' LIMIT 1)),
('统计推断', '假设检验、置信区间、贝叶斯推断等统计学核心方法', '数学基础', 'L2', 3, 2,
 (SELECT id FROM ai.knowledge WHERE title = '概率论基础' AND knowledge_level = 'L1' LIMIT 1)),
('微积分应用', '梯度、优化理论、拉格朗日乘数法等机器学习中的数学工具', '数学基础', 'L2', 3, 2,
 (SELECT id FROM ai.knowledge WHERE title = '线性代数基础' AND knowledge_level = 'L1' LIMIT 1));

-- 5. 更新现有L3知识点的父级关系
-- 为人工智能域的L3知识点设置正确的L2父级
UPDATE ai.knowledge SET parent_knowledge_id = 
  (SELECT id FROM ai.knowledge WHERE title = '深度学习基础' AND knowledge_level = 'L2' LIMIT 1)
WHERE title IN ('Transformer架构', 'GAN生成对抗网络', '注意力机制', 'VAE变分自编码器', '扩散模型原理')
  AND knowledge_level = 'L3';

UPDATE ai.knowledge SET parent_knowledge_id = 
  (SELECT id FROM ai.knowledge WHERE title = 'CNN卷积神经网络' AND knowledge_level = 'L2' LIMIT 1)
WHERE title IN ('CNN卷积神经网络')  -- 如果有相关的L3知识点，可以在这里添加
  AND knowledge_level = 'L3';

-- 为强化学习域的L3知识点设置正确的L2父级  
UPDATE ai.knowledge SET parent_knowledge_id = 
  (SELECT id FROM ai.knowledge WHERE title = '值函数方法' AND knowledge_level = 'L2' LIMIT 1)
WHERE title IN ('Q-Learning基础', 'DQN深度解析')
  AND knowledge_level = 'L3';

UPDATE ai.knowledge SET parent_knowledge_id = 
  (SELECT id FROM ai.knowledge WHERE title = '策略梯度方法' AND knowledge_level = 'L2' LIMIT 1)
WHERE title IN ('PPO算法详解', 'Actor-Critic方法', 'DDPG算法')
  AND knowledge_level = 'L3';

-- 6. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_knowledge_level_domain ON ai.knowledge(knowledge_level, domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_parent ON ai.knowledge(parent_knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_active_level ON ai.knowledge(is_active, knowledge_level);

-- 7. 验证数据完整性
-- 检查是否所有L3知识点都有L2父级
DO $$
DECLARE
    orphan_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphan_count 
    FROM ai.knowledge 
    WHERE knowledge_level = 'L3' AND parent_knowledge_id IS NULL;
    
    IF orphan_count > 0 THEN
        RAISE WARNING 'Found % L3 knowledge points without L2 parents', orphan_count;
    END IF;
END $$;

COMMIT;

-- 查看优化后的层级分布
SELECT 
    domain,
    knowledge_level,
    COUNT(*) as count,
    STRING_AGG(title, ', ') as titles
FROM ai.knowledge 
WHERE is_active = true
GROUP BY domain, knowledge_level 
ORDER BY domain, knowledge_level; 