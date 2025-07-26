-- 基于真实课程数据重新设计知识表层级结构
-- L1: Course层 (深度强化学习、线性代数、GAN、深度学习理论等)
-- L2: Lecture层 (每个课程的具体讲座)
-- L3: 细粒度知识点 (讲座中的具体概念和技术点)

BEGIN;

-- 1. 清理现有数据，重新开始
-- 保留重要的关联关系，但重新组织层级
UPDATE ai.knowledge SET is_active = false WHERE is_active = true;

-- 2. 创建L1层级 - Course课程
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, is_active) VALUES 
-- 深度强化学习课程系列
('深度强化学习', '李宏毅教授深度强化学习课程，涵盖PPO、Q-learning、Actor-Critic等核心算法', '强化学习', 'L1', 1, 20, true),

-- 线性代数课程系列  
('线性代数', '线性代数基础课程，包含向量、矩阵、特征值等核心概念', '数学基础', 'L1', 1, 15, true),

-- GAN课程系列
('生成对抗网络', 'GAN生成对抗网络课程系列，从基础理论到高级应用', '人工智能', 'L1', 1, 25, true),

-- 深度学习理论课程
('深度学习理论', '深度学习理论基础，包含泛化性、损失函数几何等理论问题', '人工智能', 'L1', 1, 18, true),

-- 计算图与反向传播
('深度学习基础', '深度学习基础概念，包含计算图、反向传播、超参数调优等', '人工智能', 'L1', 1, 12, true);

-- 3. 创建L2层级 - Lecture讲座内容
-- 深度强化学习讲座
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('PPO算法详解', 'Proximal Policy Optimization算法原理与实现', '强化学习', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度强化学习' AND knowledge_level = 'L1'), true),

('Q-learning连续动作', 'Q-learning在连续动作空间的应用方法', '强化学习', 'L2', 4, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度强化学习' AND knowledge_level = 'L1'), true),

('Actor-Critic方法', 'Actor-Critic算法框架和实现细节', '强化学习', 'L2', 4, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度强化学习' AND knowledge_level = 'L1'), true),

('稀疏奖励处理', '强化学习中稀疏奖励问题的解决方案', '强化学习', 'L2', 4, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度强化学习' AND knowledge_level = 'L1'), true),

('模仿学习', '通过专家示范学习策略的方法', '强化学习', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度强化学习' AND knowledge_level = 'L1'), true);

-- 线性代数讲座
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('向量基础', '向量的定义、运算和几何意义', '数学基础', 'L2', 2, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '线性代数' AND knowledge_level = 'L1'), true),

('矩阵运算', '矩阵乘法、性质和基本运算规则', '数学基础', 'L2', 2, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '线性代数' AND knowledge_level = 'L1'), true),

('线性方程组', '多元一次联立方程式的求解方法', '数学基础', 'L2', 2, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '线性代数' AND knowledge_level = 'L1'), true),

('特征值与特征向量', '特征值分解的理论和计算方法', '数学基础', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '线性代数' AND knowledge_level = 'L1'), true),

('正交化与对角化', '矩阵的正交化和对角化理论', '数学基础', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '线性代数' AND knowledge_level = 'L1'), true),

('秩与子空间', '矩阵的秩和向量子空间概念', '数学基础', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '线性代数' AND knowledge_level = 'L1'), true);

-- GAN讲座系列
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('GAN基础理论', 'GAN的基本原理和数学基础', '人工智能', 'L2', 4, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '生成对抗网络' AND knowledge_level = 'L1'), true),

('WGAN与EBGAN', '改进的GAN变体：Wasserstein GAN和Energy-based GAN', '人工智能', 'L2', 5, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '生成对抗网络' AND knowledge_level = 'L1'), true),

('InfoGAN与VAE-GAN', '信息论GAN和变分自编码器GAN', '人工智能', 'L2', 5, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '生成对抗网络' AND knowledge_level = 'L1'), true),

('GAN图像编辑', 'GAN在图像编辑中的应用', '人工智能', 'L2', 4, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '生成对抗网络' AND knowledge_level = 'L1'), true),

('GAN序列生成', 'GAN在文本和序列数据生成中的应用', '人工智能', 'L2', 5, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '生成对抗网络' AND knowledge_level = 'L1'), true),

('GAN评估方法', 'GAN模型质量评估的指标和方法', '人工智能', 'L2', 4, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '生成对抗网络' AND knowledge_level = 'L1'), true);

-- 深度学习理论讲座
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('泛化性理论', '深度网络泛化能力的理论分析', '人工智能', 'L2', 5, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度学习理论' AND knowledge_level = 'L1'), true),

('损失函数几何', '深度网络损失函数的几何性质研究', '人工智能', 'L2', 5, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度学习理论' AND knowledge_level = 'L1'), true),

('局部最优问题', '深度网络是否存在局部最优解的理论分析', '人工智能', 'L2', 5, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度学习理论' AND knowledge_level = 'L1'), true);

-- 深度学习基础讲座
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('计算图与反向传播', '深度学习中的计算图构建和反向传播算法', '人工智能', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度学习基础' AND knowledge_level = 'L1'), true),

('超参数调优', '深度学习模型超参数优化策略', '人工智能', 'L2', 3, 2, 
 (SELECT id FROM ai.knowledge WHERE title = '深度学习基础' AND knowledge_level = 'L1'), true);

-- 4. 创建L3层级 - 细粒度知识点
-- PPO相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('On-Policy vs Off-Policy', 'PPO中的在线策略和离线策略区别', '强化学习', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'PPO算法详解' AND knowledge_level = 'L2'), true),

('PPO目标函数', 'PPO的Clipped Surrogate Objective函数设计', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'PPO算法详解' AND knowledge_level = 'L2'), true),

('重要性采样', 'PPO中重要性采样的理论和实现', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'PPO算法详解' AND knowledge_level = 'L2'), true),

('PPO算法实现', 'PPO算法的具体实现步骤和代码', '强化学习', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'PPO算法详解' AND knowledge_level = 'L2'), true);

-- Q-learning相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('DQN深度Q网络', 'Deep Q-Network的网络结构和训练方法', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Q-learning连续动作' AND knowledge_level = 'L2'), true),

('经验回放机制', 'Q-learning中Experience Replay的原理和作用', '强化学习', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Q-learning连续动作' AND knowledge_level = 'L2'), true),

('目标网络更新', 'Q-learning中Target Network的更新策略', '强化学习', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Q-learning连续动作' AND knowledge_level = 'L2'), true),

('连续动作空间', 'Q-learning在连续动作空间的处理方法', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Q-learning连续动作' AND knowledge_level = 'L2'), true);

-- Actor-Critic相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('Actor网络设计', 'Actor-Critic中Actor网络的结构和训练', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Actor-Critic方法' AND knowledge_level = 'L2'), true),

('Critic网络设计', 'Actor-Critic中Critic网络的价值函数估计', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Actor-Critic方法' AND knowledge_level = 'L2'), true),

('优势函数计算', 'Actor-Critic中Advantage Function的计算方法', '强化学习', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'Actor-Critic方法' AND knowledge_level = 'L2'), true);

-- 线性代数相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('向量点积', '向量点积的计算和几何意义', '数学基础', 'L3', 2, 0.5, 
 (SELECT id FROM ai.knowledge WHERE title = '向量基础' AND knowledge_level = 'L2'), true),

('向量叉积', '向量叉积的计算和几何意义', '数学基础', 'L3', 2, 0.5, 
 (SELECT id FROM ai.knowledge WHERE title = '向量基础' AND knowledge_level = 'L2'), true),

('向量空间', '向量空间的定义和性质', '数学基础', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '向量基础' AND knowledge_level = 'L2'), true),

('矩阵乘法规则', '矩阵乘法的计算规则和性质', '数学基础', 'L3', 2, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '矩阵运算' AND knowledge_level = 'L2'), true),

('逆矩阵计算', '矩阵求逆的方法和应用', '数学基础', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '矩阵运算' AND knowledge_level = 'L2'), true),

('高斯消元法', '线性方程组的高斯消元求解法', '数学基础', 'L3', 2, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '线性方程组' AND knowledge_level = 'L2'), true),

('特征值计算', '特征值的数值计算方法', '数学基础', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '特征值与特征向量' AND knowledge_level = 'L2'), true),

('对角化过程', '矩阵对角化的具体步骤', '数学基础', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '正交化与对角化' AND knowledge_level = 'L2'), true);

-- GAN相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('GAN损失函数', 'GAN的Generator和Discriminator损失函数设计', '人工智能', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'GAN基础理论' AND knowledge_level = 'L2'), true),

('GAN训练稳定性', 'GAN训练过程中的稳定性问题和解决方案', '人工智能', 'L3', 5, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'GAN基础理论' AND knowledge_level = 'L2'), true),

('模式崩塌', 'GAN训练中的Mode Collapse问题', '人工智能', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'GAN基础理论' AND knowledge_level = 'L2'), true),

('Wasserstein距离', 'WGAN中Wasserstein距离的理论基础', '人工智能', 'L3', 5, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'WGAN与EBGAN' AND knowledge_level = 'L2'), true),

('FID评估指标', 'Fréchet Inception Distance评估GAN质量', '人工智能', 'L3', 4, 1, 
 (SELECT id FROM ai.knowledge WHERE title = 'GAN评估方法' AND knowledge_level = 'L2'), true);

-- 深度学习理论相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('VC维理论', '统计学习理论中的VC维概念', '人工智能', 'L3', 5, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '泛化性理论' AND knowledge_level = 'L2'), true),

('Rademacher复杂度', '泛化误差界的Rademacher复杂度分析', '人工智能', 'L3', 5, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '泛化性理论' AND knowledge_level = 'L2'), true),

('梯度下降收敛性', '梯度下降算法的收敛性理论分析', '人工智能', 'L3', 5, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '损失函数几何' AND knowledge_level = 'L2'), true);

-- 深度学习基础相关的细粒度知识点
INSERT INTO ai.knowledge (title, description, domain, knowledge_level, difficulty_level, estimated_hours, parent_knowledge_id, is_active) VALUES 
('自动微分', '深度学习框架中的自动微分机制', '人工智能', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '计算图与反向传播' AND knowledge_level = 'L2'), true),

('链式法则', '反向传播中的链式求导法则', '人工智能', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '计算图与反向传播' AND knowledge_level = 'L2'), true),

('学习率调度', '训练过程中学习率的调整策略', '人工智能', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '超参数调优' AND knowledge_level = 'L2'), true),

('批大小选择', '批大小对训练效果的影响和选择原则', '人工智能', 'L3', 3, 1, 
 (SELECT id FROM ai.knowledge WHERE title = '超参数调优' AND knowledge_level = 'L2'), true);

-- 5. 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_knowledge_hierarchy_full ON ai.knowledge(knowledge_level, domain, is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_parent_child ON ai.knowledge(parent_knowledge_id, knowledge_level);
CREATE INDEX IF NOT EXISTS idx_knowledge_active_level_difficulty ON ai.knowledge(is_active, knowledge_level, difficulty_level);

-- 6. 验证新的层级结构
DO $$
DECLARE
    l1_count INTEGER;
    l2_count INTEGER;
    l3_count INTEGER;
    orphan_l2_count INTEGER;
    orphan_l3_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO l1_count FROM ai.knowledge WHERE knowledge_level = 'L1' AND is_active = true;
    SELECT COUNT(*) INTO l2_count FROM ai.knowledge WHERE knowledge_level = 'L2' AND is_active = true;
    SELECT COUNT(*) INTO l3_count FROM ai.knowledge WHERE knowledge_level = 'L3' AND is_active = true;
    
    SELECT COUNT(*) INTO orphan_l2_count 
    FROM ai.knowledge 
    WHERE knowledge_level = 'L2' AND parent_knowledge_id IS NULL AND is_active = true;
    
    SELECT COUNT(*) INTO orphan_l3_count 
    FROM ai.knowledge 
    WHERE knowledge_level = 'L3' AND parent_knowledge_id IS NULL AND is_active = true;
    
    RAISE NOTICE 'Knowledge hierarchy created:';
    RAISE NOTICE 'L1 (Courses): % items', l1_count;
    RAISE NOTICE 'L2 (Lectures): % items', l2_count;
    RAISE NOTICE 'L3 (Knowledge Points): % items', l3_count;
    
    IF orphan_l2_count > 0 THEN
        RAISE WARNING 'Found % L2 lectures without L1 parent courses', orphan_l2_count;
    END IF;
    
    IF orphan_l3_count > 0 THEN
        RAISE WARNING 'Found % L3 knowledge points without L2 parent lectures', orphan_l3_count;
    END IF;
END $$;

COMMIT;

-- 7. 查看新的层级分布
SELECT 
    k1.title as course,
    k1.domain,
    COUNT(k2.id) as lecture_count,
    COUNT(k3.id) as knowledge_point_count
FROM ai.knowledge k1
LEFT JOIN ai.knowledge k2 ON k2.parent_knowledge_id = k1.id AND k2.knowledge_level = 'L2'
LEFT JOIN ai.knowledge k3 ON k3.parent_knowledge_id = k2.id AND k3.knowledge_level = 'L3'
WHERE k1.knowledge_level = 'L1' AND k1.is_active = true
GROUP BY k1.id, k1.title, k1.domain
ORDER BY k1.domain, k1.title; 