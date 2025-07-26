#!/usr/bin/env python3
"""
知识图谱增强脚本 - 添加新的知识点和前置关系
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    try:
        connection_string = "postgresql://ai:ai@localhost:5432/ai"
        engine = create_engine(connection_string)
        
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("✅ 成功连接到数据库")
        return engine
        
    except Exception as e:
        logger.error(f"❌ 无法连接到数据库: {e}")
        return None

def add_new_knowledge_points(session):
    """添加新的知识点"""
    
    new_knowledge_points = [
        # 数学基础补充
        {
            "title": "微积分基础",
            "description": "微分和积分的基本概念，导数、偏导数、梯度等",
            "domain": "数学基础",
            "difficulty_level": "2",
            "estimated_hours": 20,
            "search_keywords": "微积分,导数,偏导数,梯度,积分,微分"
        },
        {
            "title": "概率统计",
            "description": "概率分布、统计推断、假设检验等统计学基础",
            "domain": "数学基础",
            "difficulty_level": "2", 
            "estimated_hours": 15,
            "search_keywords": "概率,统计,分布,贝叶斯,假设检验,置信区间"
        },
        {
            "title": "最优化理论",
            "description": "最优化问题的数学理论，拉格朗日乘数法、KKT条件等",
            "domain": "数学基础",
            "difficulty_level": "3",
            "estimated_hours": 12,
            "search_keywords": "最优化,拉格朗日,KKT,凸优化,非线性规划"
        },
        
        # 编程基础补充
        {
            "title": "NumPy基础",
            "description": "Python科学计算库NumPy的使用，数组操作、线性代数运算等",
            "domain": "编程基础",
            "difficulty_level": "1",
            "estimated_hours": 8,
            "search_keywords": "NumPy,数组,矩阵运算,科学计算,向量化"
        },
        {
            "title": "PyTorch基础",
            "description": "深度学习框架PyTorch的基本使用，张量操作、自动微分等",
            "domain": "编程基础", 
            "difficulty_level": "2",
            "estimated_hours": 15,
            "search_keywords": "PyTorch,张量,自动微分,神经网络,GPU计算"
        },
        {
            "title": "TensorFlow基础",
            "description": "深度学习框架TensorFlow的基本使用，计算图、会话等",
            "domain": "编程基础",
            "difficulty_level": "2", 
            "estimated_hours": 15,
            "search_keywords": "TensorFlow,计算图,会话,Keras,tf.data"
        },
        
        # 机器学习基础补充
        {
            "title": "损失函数设计",
            "description": "各种机器学习任务的损失函数设计原理和应用",
            "domain": "机器学习基础",
            "difficulty_level": "2",
            "estimated_hours": 6,
            "search_keywords": "损失函数,交叉熵,均方误差,Hinge,Huber"
        },
        {
            "title": "正则化技术",
            "description": "L1/L2正则化、Dropout、BatchNorm等防止过拟合的技术",
            "domain": "机器学习基础",
            "difficulty_level": "2",
            "estimated_hours": 8,
            "search_keywords": "正则化,L1,L2,Dropout,BatchNorm,过拟合"
        },
        {
            "title": "交叉验证",
            "description": "模型验证的方法，K折交叉验证、留一验证等",
            "domain": "机器学习基础",
            "difficulty_level": "2",
            "estimated_hours": 4,
            "search_keywords": "交叉验证,K折,留一验证,验证集,测试集"
        },
        
        # 深度学习基础补充
        {
            "title": "反向传播算法",
            "description": "神经网络训练的核心算法，链式法则、梯度计算等",
            "domain": "深度学习",
            "difficulty_level": "3",
            "estimated_hours": 10,
            "search_keywords": "反向传播,链式法则,梯度,BP算法,自动微分"
        },
        {
            "title": "激活函数",
            "description": "神经网络中的激活函数，ReLU、Sigmoid、Tanh等",
            "domain": "深度学习", 
            "difficulty_level": "1",
            "estimated_hours": 3,
            "search_keywords": "激活函数,ReLU,Sigmoid,Tanh,Leaky ReLU,GELU"
        },
        {
            "title": "优化算法进阶",
            "description": "深度学习中的高级优化算法，AdaGrad、RMSprop、AdamW等",
            "domain": "深度学习",
            "difficulty_level": "3", 
            "estimated_hours": 8,
            "search_keywords": "AdaGrad,RMSprop,AdamW,学习率调度,动量"
        },
        
        # 注意力机制补充
        {
            "title": "自注意力机制",
            "description": "自注意力的数学原理和实现，Query、Key、Value的概念",
            "domain": "深度学习",
            "difficulty_level": "3",
            "estimated_hours": 6,
            "search_keywords": "自注意力,Query,Key,Value,scaled dot-product"
        },
        {
            "title": "多头注意力",
            "description": "多头注意力机制，并行注意力计算和特征融合",
            "domain": "深度学习",
            "difficulty_level": "3",
            "estimated_hours": 4,
            "search_keywords": "多头注意力,Multi-head,并行计算,特征融合"
        },
        
        # 强化学习补充
        {
            "title": "马尔可夫决策过程",
            "description": "强化学习的数学基础，状态、动作、奖励、转移概率",
            "domain": "强化学习",
            "difficulty_level": "3",
            "estimated_hours": 8,
            "search_keywords": "MDP,马尔可夫,状态,动作,奖励,转移概率"
        },
        {
            "title": "贝尔曼方程",
            "description": "动态规划和价值函数的数学基础",
            "domain": "强化学习",
            "difficulty_level": "3", 
            "estimated_hours": 6,
            "search_keywords": "贝尔曼方程,动态规划,价值函数,最优性"
        },
        {
            "title": "时序差分学习",
            "description": "TD学习算法，Q学习、SARSA等",
            "domain": "强化学习",
            "difficulty_level": "3",
            "estimated_hours": 8,
            "search_keywords": "TD学习,Q学习,SARSA,时序差分,值更新"
        },
        
        # 计算机视觉补充
        {
            "title": "图像预处理",
            "description": "图像数据的预处理技术，归一化、数据增强等",
            "domain": "计算机视觉",
            "difficulty_level": "1",
            "estimated_hours": 4,
            "search_keywords": "图像预处理,归一化,数据增强,裁剪,旋转"
        },
        {
            "title": "卷积操作",
            "description": "卷积神经网络的核心操作，卷积核、步长、填充等",
            "domain": "计算机视觉",
            "difficulty_level": "2",
            "estimated_hours": 6,
            "search_keywords": "卷积,卷积核,步长,填充,特征图"
        },
        {
            "title": "池化操作",
            "description": "最大池化、平均池化等降采样技术",
            "domain": "计算机视觉",
            "difficulty_level": "1",
            "estimated_hours": 2,
            "search_keywords": "池化,最大池化,平均池化,降采样"
        },
        
        # 自然语言处理补充
        {
            "title": "文本预处理",
            "description": "文本数据的清洗、分词、标准化等预处理技术",
            "domain": "自然语言处理",
            "difficulty_level": "1",
            "estimated_hours": 4,
            "search_keywords": "文本预处理,分词,清洗,标准化,停用词"
        },
        {
            "title": "序列到序列模型",
            "description": "Seq2Seq模型架构，编码器-解码器结构",
            "domain": "自然语言处理",
            "difficulty_level": "3",
            "estimated_hours": 8,
            "search_keywords": "Seq2Seq,编码器,解码器,序列建模"
        },
        
        # 模型部署和工程
        {
            "title": "模型序列化",
            "description": "模型的保存和加载，ONNX、TensorRT等格式转换",
            "domain": "AI工程",
            "difficulty_level": "2",
            "estimated_hours": 6,
            "search_keywords": "模型序列化,ONNX,TensorRT,模型转换,部署"
        },
        {
            "title": "模型量化",
            "description": "模型压缩技术，8位量化、剪枝等",
            "domain": "AI工程",
            "difficulty_level": "3",
            "estimated_hours": 8,
            "search_keywords": "模型量化,8位量化,剪枝,模型压缩,加速"
        },
        {
            "title": "分布式训练",
            "description": "多GPU、多机器的分布式深度学习训练",
            "domain": "AI工程",
            "difficulty_level": "4",
            "estimated_hours": 12,
            "search_keywords": "分布式训练,多GPU,数据并行,模型并行"
        }
    ]
    
    added_count = 0
    for kp in new_knowledge_points:
        try:
            # 检查是否已存在
            existing = session.execute(text("""
                SELECT id FROM knowledge WHERE title = :title
            """), {"title": kp["title"]}).fetchone()
            
            if existing:
                logger.info(f"知识点已存在，跳过: {kp['title']}")
                continue
                
            # 插入新知识点（不指定ID，让数据库自动生成）
            result = session.execute(text("""
                INSERT INTO knowledge (title, description, domain, difficulty_level, 
                                     estimated_hours, search_keywords, is_active, created_at)
                VALUES (:title, :description, :domain, :difficulty_level, 
                        :estimated_hours, :search_keywords, true, :created_at)
                RETURNING id
            """), {
                **kp,
                "created_at": datetime.now()
            })
            
            session.commit()  # 立即提交每个知识点
            
            new_id = result.fetchone()[0]
            logger.info(f"✅ 添加知识点: {kp['title']} (ID: {new_id})")
            added_count += 1
            
        except Exception as e:
            logger.error(f"❌ 添加知识点失败 {kp['title']}: {e}")
            session.rollback()  # 回滚当前失败的事务
    
    logger.info(f"成功添加 {added_count} 个知识点")
    return added_count

def add_prerequisite_relationships(session):
    """添加前置关系"""
    
    # 定义前置关系 (知识点标题 -> 前置知识点标题)
    prerequisite_relationships = [
        # 数学基础内部关系
        ("微积分基础", "线性代数"),
        ("最优化理论", "微积分基础"),
        ("最优化理论", "线性代数"),
        ("概率统计", "微积分基础"),
        
        # 编程基础关系
        ("NumPy基础", "Python编程基础"),
        ("PyTorch基础", "NumPy基础"),
        ("TensorFlow基础", "NumPy基础"),
        ("PyTorch基础", "Python编程基础"),
        ("TensorFlow基础", "Python编程基础"),
        
        # 机器学习基础关系
        ("损失函数设计", "微积分基础"),
        ("损失函数设计", "概率统计"),
        ("正则化技术", "损失函数设计"),
        ("交叉验证", "概率统计"),
        ("监督学习", "损失函数设计"),
        ("监督学习", "交叉验证"),
        ("无监督学习", "概率统计"),
        ("模型评估", "交叉验证"),
        ("过拟合与欠拟合", "正则化技术"),
        
        # 深度学习关系  
        ("激活函数", "微积分基础"),
        ("反向传播算法", "微积分基础"),
        ("反向传播算法", "激活函数"),
        ("优化算法进阶", "反向传播算法"),
        ("优化算法进阶", "随机梯度下降"),
        ("Adam优化器", "优化算法进阶"),
        
        # 注意力机制关系
        ("自注意力机制", "线性代数"),
        ("自注意力机制", "反向传播算法"),
        ("多头注意力", "自注意力机制"),
        ("注意力机制", "自注意力机制"),
        ("Transformer架构", "多头注意力"),
        
        # 神经网络架构关系
        ("循环神经网络(RNN)", "反向传播算法"),
        ("卷积神经网络(CNN)", "反向传播算法"),
        ("卷积神经网络(CNN)", "卷积操作"),
        ("残差网络(ResNet)", "卷积神经网络(CNN)"),
        ("生成对抗网络(GAN)", "深度学习基础"),
        ("变分自编码器(VAE)", "概率统计"),
        ("变分自编码器(VAE)", "深度学习基础"),
        
        # 强化学习关系
        ("马尔可夫决策过程", "概率统计"),
        ("贝尔曼方程", "马尔可夫决策过程"),
        ("时序差分学习", "贝尔曼方程"),
        ("强化学习基础", "马尔可夫决策过程"),
        ("DQN深度Q网络", "时序差分学习"),
        ("DQN深度Q网络", "深度学习基础"),
        ("Actor-Critic方法", "贝尔曼方程"),
        ("Actor-Critic方法", "深度学习基础"),
        ("PPO算法详解", "Actor-Critic方法"),
        ("探索与利用平衡", "强化学习基础"),
        ("稀疏奖励问题", "探索与利用平衡"),
        
        # 计算机视觉关系
        ("图像预处理", "NumPy基础"),
        ("卷积操作", "线性代数"),
        ("池化操作", "卷积操作"),
        ("图像分类", "卷积神经网络(CNN)"),
        ("图像分类", "图像预处理"),
        ("目标检测", "图像分类"),
        ("语义分割", "卷积神经网络(CNN)"),
        ("图像生成", "生成对抗网络(GAN)"),
        
        # 自然语言处理关系
        ("文本预处理", "Python编程基础"),
        ("词嵌入", "文本预处理"),
        ("序列到序列模型", "循环神经网络(RNN)"),
        ("机器翻译", "序列到序列模型"),
        ("机器翻译", "Transformer架构"),
        ("问答系统", "Transformer架构"),
        ("情感分析", "词嵌入"),
        ("命名实体识别", "词嵌入"),
        
        # AI工程关系
        ("模型序列化", "PyTorch基础"),
        ("模型序列化", "TensorFlow基础"),
        ("模型量化", "模型序列化"),
        ("分布式训练", "PyTorch基础"),
        ("分布式训练", "优化算法进阶"),
        
        # 跨领域高级关系
        ("GAN基础理论", "生成对抗网络(GAN)"),
        ("GAN训练稳定性", "GAN基础理论"),
        ("GAN损失函数", "GAN基础理论"),
        ("Transformer架构", "深度学习基础"),
        ("深度强化学习", "强化学习基础"),
        ("深度强化学习", "深度学习基础"),
    ]
    
    added_count = 0
    for knowledge_title, prerequisite_title in prerequisite_relationships:
        try:
            # 获取知识点ID
            knowledge_result = session.execute(text("""
                SELECT id FROM knowledge WHERE title = :title AND is_active = true
            """), {"title": knowledge_title}).fetchone()
            
            prerequisite_result = session.execute(text("""
                SELECT id FROM knowledge WHERE title = :title AND is_active = true  
            """), {"title": prerequisite_title}).fetchone()
            
            if not knowledge_result:
                logger.warning(f"知识点不存在: {knowledge_title}")
                continue
                
            if not prerequisite_result:
                logger.warning(f"前置知识点不存在: {prerequisite_title}")
                continue
                
            knowledge_id = knowledge_result[0]
            prerequisite_id = prerequisite_result[0]
            
            # 检查关系是否已存在
            existing = session.execute(text("""
                SELECT 1 FROM knowledge_prerequisites 
                WHERE knowledge_id = :kid AND prerequisite_id = :pid
            """), {"kid": knowledge_id, "pid": prerequisite_id}).fetchone()
            
            if existing:
                continue
                
            # 添加前置关系
            session.execute(text("""
                INSERT INTO knowledge_prerequisites (knowledge_id, prerequisite_id)
                VALUES (:kid, :pid)
            """), {"kid": knowledge_id, "pid": prerequisite_id})
            
            logger.info(f"✅ 添加前置关系: {knowledge_title} <- {prerequisite_title}")
            added_count += 1
            
        except Exception as e:
            logger.error(f"❌ 添加前置关系失败 {knowledge_title} <- {prerequisite_title}: {e}")
    
    session.commit()
    logger.info(f"成功添加 {added_count} 个前置关系")
    return added_count

def print_statistics(session):
    """打印统计信息"""
    
    print("\n" + "="*60)
    print("📊 知识图谱优化后统计")
    print("="*60)
    
    # 总体统计
    result = session.execute(text("""
        SELECT 
            COUNT(*) as total_knowledge,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_knowledge
        FROM knowledge
    """)).fetchone()
    
    prereq_count = session.execute(text("""
        SELECT COUNT(*) FROM knowledge_prerequisites
    """)).fetchone()[0]
    
    print(f"总知识点数: {result[0]}")
    print(f"活跃知识点数: {result[1]}")
    print(f"前置关系数: {prereq_count}")
    
    # 按领域统计
    domain_stats = session.execute(text("""
        SELECT domain, COUNT(*) as count
        FROM knowledge 
        WHERE is_active = true
        GROUP BY domain 
        ORDER BY count DESC
    """)).fetchall()
    
    print(f"\n按领域分布:")
    for domain, count in domain_stats:
        print(f"  {domain}: {count}个")
    
    # 前置关系密度统计
    coverage_stats = session.execute(text("""
        SELECT 
            COUNT(DISTINCT kp.knowledge_id) as knowledge_with_prereqs,
            COUNT(DISTINCT kp.prerequisite_id) as knowledge_as_prereqs
        FROM knowledge_prerequisites kp
    """)).fetchone()
    
    print(f"\n前置关系覆盖:")
    print(f"  有前置关系的知识点: {coverage_stats[0]}个")
    print(f"  作为前置条件的知识点: {coverage_stats[1]}个")
    print(f"  前置关系密度: {prereq_count/result[1]:.2f} (平均每个知识点)")

def main():
    """主函数"""
    print("🚀 开始优化知识图谱")
    print("="*60)
    
    # 获取数据库连接
    engine = get_db_connection()
    if not engine:
        return
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 添加新知识点
        print("\n📚 添加新知识点...")
        knowledge_added = add_new_knowledge_points(session)
        
        # 2. 添加前置关系
        print("\n🔗 添加前置关系...")
        relationships_added = add_prerequisite_relationships(session)
        
        # 3. 打印统计信息
        print_statistics(session)
        
        print(f"\n🎉 优化完成!")
        print(f"✅ 新增知识点: {knowledge_added}个")
        print(f"✅ 新增前置关系: {relationships_added}个")
        
    except Exception as e:
        logger.error(f"❌ 优化过程出错: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()