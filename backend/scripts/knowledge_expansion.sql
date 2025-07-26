-- 扩展知识点插入语句
-- 作者：AI课程设计师
-- 生成时间：2025-07-26 03:02:26.924272

-- 知识点插入语句

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (100, '强化学习基础', '强化学习的基本概念、马尔可夫决策过程和基础算法', '深度強化學習', 2, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (101, '马尔可夫决策过程', 'MDP的定义、状态转移、奖励函数等基础概念', '深度強化學習', 2, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (102, 'Q-Learning算法', '经典的无模型强化学习算法，基于价值函数的学习', '深度強化學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (103, '策略梯度方法', '基于策略的强化学习方法，直接优化策略函数', '深度強化學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (104, '价值函数近似', '使用函数近似来估计状态价值和动作价值', '深度強化學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (105, '深度Q网络(DQN)', '结合深度神经网络和Q-Learning的突破性算法', '深度強化學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (106, 'DQN基础架构', '深度Q网络的基本结构和训练过程', '深度強化學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (107, '经验回放机制', 'Experience Replay在DQN中的作用和实现', '深度強化學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (108, '目标网络更新', 'Target Network的稳定训练机制', '深度強化學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (109, 'Double DQN', '解决Q值高估问题的改进算法', '深度強化學習', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (110, '策略优化算法', '现代强化学习中的高级策略优化方法', '深度強化學習', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (111, 'REINFORCE算法', '最基础的策略梯度算法实现', '深度強化學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (112, 'Actor-Critic方法', '结合价值函数和策略函数的混合方法', '深度強化學習', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (113, 'Proximal Policy Optimization', 'PPO算法的原理、实现和优势', '深度強化學習', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (114, 'Trust Region Policy Optimization', 'TRPO算法的约束优化方法', '深度強化學習', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (115, '多智能体强化学习', '多个智能体环境下的强化学习方法和挑战', '深度強化學習', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (116, '独立学习', '每个智能体独立进行强化学习的方法', '深度強化學習', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (117, '协作学习', '智能体之间协作完成任务的学习方法', '深度強化學習', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (118, '竞争学习', '智能体之间竞争环境下的学习策略', '深度強化學習', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (119, '通信机制', '智能体间的信息交换和协调机制', '深度強化學習', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (120, '监督学习基础', '基于标注数据的机器学习方法', '機器學習', 2, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (121, '线性回归', '最基础的回归算法，建立输入与输出的线性关系', '機器學習', 2, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (122, '逻辑回归', '用于分类任务的线性模型', '機器學習', 2, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (123, '支持向量机', '基于最大间隔的分类和回归算法', '機器學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (124, '决策树', '基于树形结构的分类和回归方法', '機器學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (125, '随机森林', '基于多个决策树的集成学习方法', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (126, '无监督学习', '不需要标注数据的机器学习方法', '機器學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (127, 'K-means聚类', '基于距离的经典聚类算法', '機器學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (128, '层次聚类', '基于层级结构的聚类方法', '機器學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (129, '主成分分析', 'PCA降维算法的原理和应用', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (130, 't-SNE降维', '非线性降维方法用于数据可视化', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (131, '深度学习基础', '神经网络和深度学习的基础理论', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (132, '感知机模型', '最简单的神经网络模型', '機器學習', 3, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (133, '多层感知机', '多层神经网络的结构和训练', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (134, '反向传播算法', '神经网络训练的核心算法', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (135, '激活函数', '神经网络中的非线性激活函数', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (136, '正则化技术', '防止过拟合的各种方法', '機器學習', 4, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (137, '生成对抗网络', 'GAN及其变种的原理和应用', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (138, 'GAN基础原理', '生成器和判别器的对抗训练机制', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (139, 'DCGAN架构', '深度卷积生成对抗网络', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (140, '条件GAN', '基于条件的生成对抗网络', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (141, 'StyleGAN', '高质量图像生成的GAN变种', '生成式AI', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (142, '扩散模型', '基于扩散过程的生成模型', '生成式AI', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (143, 'DDPM原理', '去噪扩散概率模型的基础理论', '生成式AI', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (144, '扩散过程', '前向和反向扩散过程的数学原理', '生成式AI', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (145, 'Stable Diffusion', '稳定扩散模型的架构和应用', '生成式AI', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (146, '文本到图像生成', '基于文本描述的图像生成技术', '生成式AI', 6, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (147, '大语言模型', '大规模语言模型的架构和应用', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (148, 'Transformer架构', '注意力机制和Transformer模型', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (149, 'BERT模型', '双向编码器表示模型', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (150, 'GPT系列', '生成式预训练Transformer模型', '生成式AI', 5, NOW());

INSERT INTO ai.knowledge (id, title, description, domain, difficulty_level, created_at) 
VALUES (151, '提示工程', '优化大语言模型输出的技术', '生成式AI', 4, NOW());

-- 知识依赖关系插入语句

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (101, 100, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (102, 100, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (103, 100, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (104, 100, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (106, 105, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (107, 105, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (108, 105, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (109, 105, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (111, 110, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (112, 110, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (113, 110, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (114, 110, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (116, 115, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (117, 115, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (118, 115, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (119, 115, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (121, 120, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (122, 120, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (123, 120, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (124, 120, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (125, 120, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (127, 126, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (128, 126, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (129, 126, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (130, 126, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (132, 131, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (133, 131, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (134, 131, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (135, 131, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (136, 131, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (138, 137, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (139, 137, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (140, 137, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (141, 137, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (143, 142, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (144, 142, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (145, 142, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (146, 142, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (148, 147, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (149, 147, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (150, 147, NOW());

INSERT INTO ai.knowledge_prerequisites (knowledge_id, prerequisite_id, created_at) 
VALUES (151, 147, NOW());
