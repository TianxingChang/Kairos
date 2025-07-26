#!/usr/bin/env python3
"""
Script to expand the knowledge database with more comprehensive knowledge points.
This adds knowledge points for common ML/AI topics that might not be covered in the current video content.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import get_db
from db.models import Knowledge
from sqlalchemy.orm import Session

def expand_knowledge_database():
    """Add comprehensive knowledge points to the database."""
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Deep Learning Architecture Knowledge Points
        deep_learning_knowledge = [
            {
                "title": "卷积神经网络(CNN)",
                "description": "专门用于处理图像数据的神经网络架构，使用卷积层、池化层等组件提取图像特征",
                "domain": "深度学习",
                "difficulty_level": "中级",
                "search_keywords": "CNN, 卷积, 池化, 图像处理, 特征提取, LeNet, AlexNet, ResNet"
            },
            {
                "title": "循环神经网络(RNN)", 
                "description": "专门处理序列数据的神经网络，能够记忆历史信息，适合自然语言处理和时序预测",
                "domain": "深度学习",
                "difficulty_level": "中级", 
                "search_keywords": "RNN, LSTM, GRU, 序列, 时序, 记忆, 自然语言处理"
            },
            {
                "title": "生成对抗网络(GAN)",
                "description": "由生成器和判别器组成的对抗训练框架，用于生成逼真的数据样本",
                "domain": "深度学习",
                "difficulty_level": "高级",
                "search_keywords": "GAN, 生成器, 判别器, 对抗训练, 数据生成, StyleGAN, DCGAN"
            },
            {
                "title": "变分自编码器(VAE)",
                "description": "结合变分推理和自编码器的生成模型，能够学习数据的潜在表示并生成新样本",
                "domain": "深度学习", 
                "difficulty_level": "高级",
                "search_keywords": "VAE, 变分推理, 自编码器, 潜在空间, 生成模型, KL散度"
            },
            {
                "title": "注意力机制",
                "description": "让模型关注输入序列中重要部分的机制，是Transformer架构的核心组件",
                "domain": "深度学习",
                "difficulty_level": "中级",
                "search_keywords": "注意力, Attention, Self-Attention, Multi-Head, Query, Key, Value"
            },
            {
                "title": "残差网络(ResNet)",
                "description": "通过跳跃连接解决深度网络梯度消失问题的架构，使得训练超深网络成为可能",
                "domain": "深度学习",
                "difficulty_level": "中级", 
                "search_keywords": "ResNet, 残差连接, 跳跃连接, 梯度消失, 深度网络"
            }
        ]
        
        # Computer Vision Knowledge Points
        cv_knowledge = [
            {
                "title": "图像分类",
                "description": "将图像分配到预定义类别的任务，是计算机视觉的基础问题",
                "domain": "计算机视觉",
                "difficulty_level": "初级",
                "search_keywords": "图像分类, 分类器, ImageNet, 特征提取, 预训练模型"
            },
            {
                "title": "目标检测", 
                "description": "在图像中定位和识别多个目标的任务，输出目标的位置和类别",
                "domain": "计算机视觉",
                "difficulty_level": "中级",
                "search_keywords": "目标检测, YOLO, R-CNN, 边界框, 锚框, 非极大值抑制"
            },
            {
                "title": "语义分割",
                "description": "为图像中的每个像素分配语义标签的密集预测任务",
                "domain": "计算机视觉",
                "difficulty_level": "中级",
                "search_keywords": "语义分割, 像素级分类, U-Net, FCN, DeepLab"
            },
            {
                "title": "图像生成",
                "description": "使用深度学习模型生成新的图像内容，包括无条件和条件生成",
                "domain": "计算机视觉",
                "difficulty_level": "高级",
                "search_keywords": "图像生成, Diffusion, DALL-E, Stable Diffusion, 条件生成"
            }
        ]
        
        # Natural Language Processing Knowledge Points
        nlp_knowledge = [
            {
                "title": "词嵌入",
                "description": "将词汇映射到连续向量空间的技术，捕获词汇的语义关系",
                "domain": "自然语言处理",
                "difficulty_level": "初级",
                "search_keywords": "词嵌入, Word2Vec, GloVe, FastText, 语义向量"
            },
            {
                "title": "命名实体识别",
                "description": "从文本中识别和分类命名实体(如人名、地名、机构名)的任务",
                "domain": "自然语言处理", 
                "difficulty_level": "中级",
                "search_keywords": "NER, 命名实体, 序列标注, CRF, BERT-NER"
            },
            {
                "title": "情感分析",
                "description": "分析文本情感倾向的任务，判断文本表达的情感是正面、负面还是中性",
                "domain": "自然语言处理",
                "difficulty_level": "初级", 
                "search_keywords": "情感分析, 情感分类, 极性分析, 情感词典"
            },
            {
                "title": "机器翻译",
                "description": "将一种语言的文本自动翻译成另一种语言的任务",
                "domain": "自然语言处理",
                "difficulty_level": "高级",
                "search_keywords": "机器翻译, 序列到序列, 注意力机制, BLEU, 神经机器翻译"
            },
            {
                "title": "问答系统",
                "description": "根据给定问题和上下文信息自动生成答案的系统",
                "domain": "自然语言处理",
                "difficulty_level": "高级", 
                "search_keywords": "问答系统, QA, 阅读理解, SQuAD, 检索增强生成"
            }
        ]
        
        # Machine Learning Fundamentals Knowledge Points  
        ml_knowledge = [
            {
                "title": "监督学习",
                "description": "使用标注数据训练模型的学习方式，包括分类和回归任务",
                "domain": "机器学习基础",
                "difficulty_level": "初级",
                "search_keywords": "监督学习, 标注数据, 分类, 回归, 训练集, 测试集"
            },
            {
                "title": "无监督学习", 
                "description": "在没有标注数据的情况下发现数据中隐藏模式的学习方式",
                "domain": "机器学习基础",
                "difficulty_level": "中级",
                "search_keywords": "无监督学习, 聚类, 降维, PCA, K-means, 异常检测"
            },
            {
                "title": "过拟合与欠拟合",
                "description": "模型复杂度与泛化能力之间的权衡问题，以及相应的解决方法",
                "domain": "机器学习基础", 
                "difficulty_level": "初级",
                "search_keywords": "过拟合, 欠拟合, 泛化, 正则化, 交叉验证, 模型复杂度"
            },
            {
                "title": "特征工程",
                "description": "从原始数据中提取和构造有用特征以提升模型性能的过程",
                "domain": "机器学习基础",
                "difficulty_level": "中级",
                "search_keywords": "特征工程, 特征选择, 特征提取, 数据预处理, 特征缩放"
            },
            {
                "title": "模型评估",
                "description": "使用各种指标和方法评估机器学习模型性能的技术",
                "domain": "机器学习基础",
                "difficulty_level": "初级", 
                "search_keywords": "模型评估, 准确率, 精确率, 召回率, F1分数, ROC曲线, AUC"
            },
            {
                "title": "集成学习",
                "description": "组合多个模型以获得更好预测性能的方法",
                "domain": "机器学习基础",
                "difficulty_level": "中级",
                "search_keywords": "集成学习, 随机森林, 梯度提升, AdaBoost, XGBoost, 投票法"
            }
        ]
        
        # Optimization Knowledge Points
        optimization_knowledge = [
            {
                "title": "随机梯度下降",
                "description": "使用随机采样的小批次数据来近似梯度的优化算法",
                "domain": "优化算法",
                "difficulty_level": "初级",
                "search_keywords": "SGD, 随机梯度下降, 小批次, 学习率, 动量"
            },
            {
                "title": "Adam优化器",
                "description": "结合动量和自适应学习率的高效优化算法",
                "domain": "优化算法", 
                "difficulty_level": "中级",
                "search_keywords": "Adam, 自适应学习率, 动量, RMSprop, 优化器"
            },
            {
                "title": "学习率调度",
                "description": "在训练过程中动态调整学习率以提升收敛效果的策略",
                "domain": "优化算法",
                "difficulty_level": "中级",
                "search_keywords": "学习率调度, 学习率衰减, 余弦退火, 热重启"
            }
        ]
        
        # Combine all knowledge points
        all_knowledge = (deep_learning_knowledge + cv_knowledge + nlp_knowledge + 
                        ml_knowledge + optimization_knowledge)
        
        # Insert knowledge points into database
        added_count = 0
        for kp_data in all_knowledge:
            # Check if knowledge point already exists
            existing = db.query(Knowledge).filter(
                Knowledge.title == kp_data["title"]
            ).first()
            
            if not existing:
                knowledge_point = Knowledge(**kp_data)
                db.add(knowledge_point)
                added_count += 1
                print(f"Added: {kp_data['title']}")
            else:
                print(f"Skipped (exists): {kp_data['title']}")
        
        db.commit()
        print(f"\n✅ Successfully added {added_count} new knowledge points to the database")
        print(f"📊 Total knowledge points processed: {len(all_knowledge)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error expanding knowledge database: {str(e)}")
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Expanding knowledge database...")
    expand_knowledge_database()
    print("✨ Done!")