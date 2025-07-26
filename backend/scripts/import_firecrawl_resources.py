#!/usr/bin/env python3
"""
Script to import firecrawl data as learning resources into the database.
This processes the crawled content and creates learning resources and knowledge point associations.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to Python path for imports
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
project_root = backend_dir.parent
sys.path.append(str(backend_dir))

from db.session import get_db
from db.models import LearningResource, Knowledge, knowledge_resource_association
from sqlalchemy.orm import Session
from sqlalchemy import text

def process_firecrawl_data():
    """Process and import firecrawl data into the database."""
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        firecrawl_base_path = project_root / "data" / "firecrawl"
        
        if not firecrawl_base_path.exists():
            print(f"❌ Firecrawl data directory not found: {firecrawl_base_path}")
            return
        
        # Process each crawl result directory
        crawl_dirs = [d for d in firecrawl_base_path.iterdir() if d.is_dir()]
        print(f"📁 Found {len(crawl_dirs)} crawl result directories")
        
        total_processed = 0
        total_resources = 0
        
        for crawl_dir in crawl_dirs:
            print(f"\n🔍 Processing: {crawl_dir.name}")
            
            # Look for page_content.json
            page_content_file = crawl_dir / "page_content.json"
            if page_content_file.exists():
                resources_added = process_page_content(db, page_content_file, crawl_dir.name)
                total_resources += resources_added
            
            # Process video info files
            video_files = list(crawl_dir.glob("*_info.json"))
            for video_file in video_files:
                video_added = process_video_info(db, video_file, crawl_dir.name)
                total_processed += video_added
        
        # Associate resources with knowledge points based on content similarity
        print(f"\n🔗 Creating knowledge-resource associations...")
        create_knowledge_associations(db)
        
        db.commit()
        print(f"\n✅ Import completed successfully!")
        print(f"📊 Total resources added: {total_resources}")
        print(f"🎥 Total video metadata processed: {total_processed}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error importing firecrawl data: {str(e)}")
        raise
    
    finally:
        db.close()

def process_page_content(db: Session, page_content_file: Path, source_name: str) -> int:
    """Process page_content.json file and create learning resource."""
    
    try:
        with open(page_content_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract relevant information
        title = data.get('metadata', {}).get('title', 'Unknown Title')
        url = data.get('actual_url', data.get('target_url', ''))
        markdown_content = data.get('markdown', '')
        
        # Check if resource already exists
        existing = db.query(LearningResource).filter(
            LearningResource.resource_url == url
        ).first()
        
        if existing:
            print(f"⏭️  Skipped (exists): {title}")
            return 0
        
        # Create learning resource
        resource = LearningResource(
            title=title,
            resource_type="webpage",
            resource_url=url,
            description=f"Web content from {source_name}",
            transcript=markdown_content[:10000] if markdown_content else "",  # Limit size
            language="zh",
            is_available=True
        )
        
        db.add(resource)
        db.flush()  # Get the ID
        
        print(f"✅ Added webpage: {title}")
        return 1
        
    except Exception as e:
        print(f"❌ Error processing page content {page_content_file}: {str(e)}")
        return 0

def process_video_info(db: Session, video_info_file: Path, source_name: str) -> int:
    """Process video info JSON file and create learning resource."""
    
    try:
        with open(video_info_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract video information
        title = data.get('title', 'Unknown Video')
        video_id = data.get('id', '')
        duration = data.get('duration', 0)
        description = data.get('description', '')
        url = data.get('webpage_url', f"https://youtube.com/watch?v={video_id}")
        
        # Check if resource already exists
        existing = db.query(LearningResource).filter(
            LearningResource.resource_url == url
        ).first()
        
        if existing:
            print(f"⏭️  Skipped (exists): {title}")
            return 0
        
        # Look for transcript files
        transcript_content = ""
        video_base_name = video_info_file.stem.replace('_info', '')
        
        # Try different transcript file extensions
        transcript_files = [
            video_info_file.parent / f"{video_base_name}.zh-TW.vtt",
            video_info_file.parent / f"{video_base_name}.zh-Hant.vtt",
            video_info_file.parent / f"{video_base_name}.en.vtt"
        ]
        
        for transcript_file in transcript_files:
            if transcript_file.exists():
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        transcript_content = f.read()
                    break
                except:
                    continue
        
        # Create learning resource
        resource = LearningResource(
            title=title,
            resource_type="video",
            resource_url=url,
            description=description[:1000] if description else f"Video from {source_name}",
            transcript=transcript_content[:20000] if transcript_content else "",  # Limit size
            duration_minutes=duration // 60 if duration else None,
            language="zh",
            is_available=True
        )
        
        db.add(resource)
        db.flush()  # Get the ID
        
        print(f"✅ Added video: {title}")
        return 1
        
    except Exception as e:
        print(f"❌ Error processing video info {video_info_file}: {str(e)}")
        return 0

def create_knowledge_associations(db: Session) -> None:
    """Create associations between learning resources and knowledge points based on content matching."""
    
    try:
        # Get all resources without existing associations
        resources = db.query(LearningResource).filter(
            ~LearningResource.knowledge_points.any()
        ).all()
        
        # Get all active knowledge points
        knowledge_points = db.query(Knowledge).filter(
            Knowledge.is_active == True
        ).all()
        
        associations_created = 0
        
        for resource in resources:
            # Combine title, description, and transcript for matching
            content = f"{resource.title} {resource.description or ''} {resource.transcript or ''}"
            content_lower = content.lower()
            
            matched_knowledge = []
            
            for kp in knowledge_points:
                # Check if knowledge point keywords match resource content
                keywords = kp.search_keywords or ""
                title_lower = kp.title.lower()
                
                # Simple keyword matching
                if (title_lower in content_lower or 
                    any(keyword.strip().lower() in content_lower 
                        for keyword in keywords.split(',') if keyword.strip())):
                    matched_knowledge.append(kp)
            
            # Create associations for matched knowledge points
            for kp in matched_knowledge:
                # Check if association already exists
                existing = db.execute(
                    text("SELECT 1 FROM knowledge_resource_association WHERE knowledge_id = :kid AND resource_id = :rid"),
                    {"kid": kp.id, "rid": resource.id}
                ).fetchone()
                
                if not existing:
                    db.execute(
                        text("INSERT INTO knowledge_resource_association (knowledge_id, resource_id) VALUES (:kid, :rid)"),
                        {"kid": kp.id, "rid": resource.id}
                    )
                    associations_created += 1
                    print(f"🔗 Associated '{resource.title[:50]}...' with '{kp.title}'")
        
        print(f"✅ Created {associations_created} knowledge-resource associations")
        
    except Exception as e:
        print(f"❌ Error creating knowledge associations: {str(e)}")
        raise

if __name__ == "__main__":
    print("🚀 Importing firecrawl data as learning resources...")
    process_firecrawl_data()
    print("✨ Done!")