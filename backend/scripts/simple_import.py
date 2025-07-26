#!/usr/bin/env python3
"""
简单批量导入学习资源到数据库的脚本（不进行VTT分析）
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from db.session import SessionLocal
from db.models import Knowledge, LearningResource


class SimpleResourceImporter:
    """简单资源导入器（只导入基础信息，不进行AI分析）"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.domains = {
            "生成式AI": ["生成式AI", "GenAI", "Generative AI", "GPT", "LLM", "語言模型", "Transformer", "ChatGPT"],
            "機器學習": ["機器學習", "Machine Learning", "ML", "模型", "深度學習", "神經網路", "可解釋", "Explainable"],
            "深度強化學習": ["强化學習", "Reinforcement Learning", "RL", "DRL", "Policy", "Q-learning", "PPO", "Actor", "Critic"],
            "計算機視覺": ["Computer Vision", "CV", "Image", "Vision", "圖像", "視覺", "CNN", "Diffusion"],
            "自然語言處理": ["NLP", "Natural Language", "語言處理", "文本", "Text"],
            "AI倫理與安全": ["AI倫理", "AI安全", "偏見", "安全性", "Ethics", "Safety", "Bias", "倫理"]
        }
    
    def detect_domain(self, title: str, description: str = "") -> str:
        """根據標題和描述檢測學科領域"""
        text = f"{title} {description}".lower()
        
        # 計算每個領域的匹配分數
        domain_scores = {}
        for domain, keywords in self.domains.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1
            domain_scores[domain] = score
        
        # 返回得分最高的領域
        best_domain = max(domain_scores, key=domain_scores.get)
        if domain_scores[best_domain] > 0:
            return best_domain
        else:
            return "通用AI"  # 默認領域
    
    def extract_title_from_filename(self, filename: str) -> str:
        """從文件名提取標題"""
        # 移除文件擴展名
        title = Path(filename).stem
        
        # 清理常見的模式
        title = re.sub(r'\.zh-TW$', '', title)
        title = re.sub(r'\.en$', '', title)
        title = re.sub(r'_info$', '', title)
        
        # 替換下劃線為空格
        title = title.replace('_', ' ')
        
        return title.strip()
    
    def get_resource_type(self, filename: str) -> str:
        """根據文件擴展名確定資源類型"""
        ext = Path(filename).suffix.lower()
        
        type_mapping = {
            '.mp4': 'video',
            '.webm': 'video', 
            '.avi': 'video',
            '.vtt': 'subtitle',
            '.srt': 'subtitle',
            '.pdf': 'document',
            '.pptx': 'presentation',
            '.ppt': 'presentation',
            '.txt': 'text',
            '.md': 'text',
            '.json': 'data',
            '.description': 'description'
        }
        
        return type_mapping.get(ext, 'unknown')
    
    def read_description_file(self, desc_path: Path) -> str:
        """讀取描述文件內容"""
        try:
            with open(desc_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"⚠️  無法讀取描述文件 {desc_path}: {e}")
            return ""
    
    def scan_directory(self, directory: Path) -> List[Dict]:
        """掃描目錄中的學習資源"""
        resources = []
        
        # 獲取所有文件
        all_files = list(directory.glob('*'))
        
        # 按照主文件分組 (基於文件名前綴)
        file_groups = {}
        
        for file_path in all_files:
            if file_path.is_file():
                # 提取基礎文件名 (不含擴展名和語言標識)
                base_name = file_path.stem
                base_name = re.sub(r'\.zh-TW$', '', base_name)
                base_name = re.sub(r'\.en$', '', base_name)
                base_name = re.sub(r'_info$', '', base_name)
                
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(file_path)
        
        # 處理每個文件組
        for base_name, files in file_groups.items():
            # 找主要資源文件 (視頻或文檔)
            main_file = None
            description_file = None
            subtitle_files = []
            
            for file_path in files:
                resource_type = self.get_resource_type(file_path.name)
                
                if resource_type in ['video', 'document', 'presentation']:
                    if main_file is None:  # 取第一個主要文件
                        main_file = file_path
                elif resource_type == 'description':
                    description_file = file_path
                elif resource_type == 'subtitle':
                    subtitle_files.append(file_path)
            
            # 如果找到主要文件，創建資源記錄
            if main_file:
                title = self.extract_title_from_filename(base_name)
                description = ""
                
                if description_file:
                    description = self.read_description_file(description_file)
                
                domain = self.detect_domain(title, description)
                
                resource = {
                    'title': title,
                    'resource_type': self.get_resource_type(main_file.name),
                    'resource_url': str(main_file.absolute()),
                    'description': description,
                    'domain': domain,
                    'subtitle_files': [str(f.absolute()) for f in subtitle_files],
                    'base_directory': str(directory.absolute())
                }
                
                resources.append(resource)
        
        return resources
    
    def import_basic_resource(self, resource: Dict) -> bool:
        """導入基礎資源信息到數據庫"""
        try:
            # 檢查資源是否已存在
            existing = self.db.query(LearningResource).filter(
                LearningResource.resource_url == resource['resource_url']
            ).first()
            
            if existing:
                print(f"  ⏭️  資源已存在，跳過: {resource['title']}")
                self.skipped_count += 1
                return True
            
            # 創建新的學習資源
            new_resource = LearningResource(
                title=resource['title'],
                resource_type=resource['resource_type'],
                resource_url=resource['resource_url'],
                description=resource['description'],
                language='zh',
                quality_score=5,  # 默認質量分數
                is_available=True
            )
            
            self.db.add(new_resource)
            self.db.commit()
            self.db.refresh(new_resource)
            
            print(f"  ✅ 導入成功: {resource['title']}")
            self.imported_count += 1
            return True
            
        except Exception as e:
            print(f"  ❌ 導入失敗: {resource['title']} - {e}")
            self.error_count += 1
            self.db.rollback()
            return False
    
    def process_directory(self, directory: str):
        """處理單個目錄"""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"❌ 目錄不存在: {directory}")
            return
        
        print(f"\n📁 處理目錄: {directory_path.name}")
        
        # 掃描資源
        resources = self.scan_directory(directory_path)
        print(f"   發現 {len(resources)} 個學習資源")
        
        # 處理每個資源
        for i, resource in enumerate(resources, 1):
            print(f"\n🎯 處理資源 {i}/{len(resources)}: {resource['title']}")
            print(f"   類型: {resource['resource_type']}, 領域: {resource['domain']}")
            
            # 導入基礎資源信息
            self.import_basic_resource(resource)
    
    def run(self, directories: List[str]):
        """運行批量導入"""
        print("🚀 開始簡單批量導入學習資源（僅基礎信息）")
        print(f"📊 待處理目錄數量: {len(directories)}")
        
        start_time = datetime.now()
        
        # 處理每個目錄
        for directory in directories:
            self.process_directory(directory)
        
        # 關閉數據庫連接
        self.db.close()
        
        # 輸出統計信息
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n" + "="*60)
        print(f"📋 簡單批量導入完成!")
        print(f"⏱️  用時: {duration}")
        print(f"✅ 成功導入: {self.imported_count} 個資源")
        print(f"⏭️  跳過已存在: {self.skipped_count} 個資源")
        print(f"❌ 導入失敗: {self.error_count} 個資源")
        print(f"📊 總處理: {self.imported_count + self.skipped_count + self.error_count} 個資源")
        print(f"\n💡 提示: 稍後可以使用 transcript_analyzer API 對VTT文件進行分析")


def main():
    """主函數"""
    # 要處理的目錄列表
    directories = [
        "data/firecrawlcrawl_results_20250725_222601",
        "data/firecrawlcrawl_results_20250725_035351", 
        "data/firecrawlcrawl_results_20250725_031705"
    ]
    
    # 創建導入器並運行
    importer = SimpleResourceImporter()
    importer.run(directories)


if __name__ == "__main__":
    main()