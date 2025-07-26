"""Main application module for web scraping learning resources.

This is completely separate from the knowledge graph generation workflow
and focuses specifically on discovering, crawling, and organizing learning content.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import argparse
from datetime import datetime
import time
import json
import os
import re
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse, unquote
from tqdm import tqdm
import yt_dlp

import sys
from pathlib import Path

# Add parent directory to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from firecrawl import FirecrawlApp, ScrapeOptions, JsonConfig
from scraping.config.firecrawl_config import FirecrawlConfig, ScrapingConfig
from scraping.models.learning_resource import ParsedCommand, CommandIntent
from utils.logging_config import setup_logging
from config.settings import Settings


logger = logging.getLogger(__name__)


class ScrapingApplication:
    """Main application class for web scraping operations."""
    
    def __init__(
        self,
        firecrawl_config: Optional[FirecrawlConfig] = None,
        scraping_config: Optional[ScrapingConfig] = None,
        settings: Optional[Settings] = None
    ):
        """Initialize the scraping application."""
        self._firecrawl_config = firecrawl_config or FirecrawlConfig.from_environment()
        self._scraping_config = scraping_config or ScrapingConfig.from_environment()
        self._settings = settings or Settings.get_default()
        
        # Initialize Firecrawl client
        self._firecrawl_app = FirecrawlApp(api_key=self._firecrawl_config.api_key)
        
        # Setup logging
        setup_logging(settings=self._settings)
        
        # Validate Firecrawl configuration
        if not self._firecrawl_config.api_key:
            raise ValueError("Firecrawl API key is required")
        if not self._firecrawl_config.api_key.startswith("fc-"):
            raise ValueError("Invalid Firecrawl API key format. Must start with 'fc-'")
        
        logger.info("ScrapingApplication initialized")
    
    async def search_learning_resources(self, topic: str) -> None:
        """Search for learning resources on a specific topic."""
        logger.info(f"Searching for learning resources on topic: {topic}")
        
        try:
            # Use Firecrawl to search and scrape content
            search_url = f"https://www.google.com/search?q={topic}+tutorial"
            
            # Use actions to interact with search results
            scrape_result = self._firecrawl_app.scrape_url(
                search_url,
                formats=['markdown', 'html'],
                actions=[
                    {"type": "wait", "milliseconds": 2000},
                    {"type": "scrape"}
                ]
            )
            
            # 直接访问属性而不是使用 get 方法
            print(f"🔍 Found learning resources for: {topic}")
            
            # Save results
            output_dir = Path(self._scraping_config.download_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"search_results_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # 构建要保存的数据
            result_data = {
                "markdown": scrape_result.markdown,
                "html": scrape_result.html,
                "metadata": scrape_result.metadata
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            print(f"📊 Results saved to: {output_file}")
            print(f"📁 Download directory: {self._scraping_config.download_directory}")
            print(f"🎯 Content types: {', '.join(self._scraping_config.content_types)}")
            
            # 打印预览
            print("\n📄 Content Preview:")
            print(f"Title: {scrape_result.metadata.get('title', 'No title')}")
            print(f"Description: {scrape_result.metadata.get('description', 'No description')}")
            print(f"\nMarkdown Preview:\n{scrape_result.markdown[:500]}...")
                
        except Exception as e:
            logger.error(f"Error searching learning resources: {e}")
            print(f"❌ Error: {e}")
    
    def _is_course_content_link(self, url: str) -> bool:
        """判断是否为课程内容链接"""
        content_patterns = [
            r'\.pdf$',
            r'\.ppt$',
            r'\.pptx$',
            r'youtube\.com/watch',
            r'youtu\.be/',
            r'drive\.google\.com',
            r'docs\.google\.com'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in content_patterns)

    def _extract_course_content(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """提取课程内容链接"""
        soup = BeautifulSoup(html, 'html.parser')
        content_links = []
        
        # 查找所有表格
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if not cells:
                    continue
                    
                content = {
                    'topic': '',
                    'pdf': '',
                    'ppt': '',
                    'video': '',
                    'homework': ''
                }
                
                # 提取每个单元格的内容
                for i, cell in enumerate(cells):
                    links = cell.find_all('a')
                    for link in links:
                        href = link.get('href', '')
                        if not href:
                            continue
                            
                        # 处理相对URL
                        if not href.startswith(('http://', 'https://')):
                            href = urljoin(base_url, href)
                            
                        text = link.get_text().strip().lower()
                        
                        # 根据链接文本和URL特征分类内容
                        if i == 0:  # 第一列通常是主题
                            content['topic'] = link.get_text().strip()
                        elif 'pdf' in text or href.lower().endswith('.pdf'):
                            content['pdf'] = href
                        elif 'ppt' in text or any(href.lower().endswith(ext) for ext in ['.ppt', '.pptx']):
                            content['ppt'] = href
                        elif 'view' in text or 'video' in text or 'youtube' in href or 'youtu.be' in href:
                            content['video'] = href
                        elif 'hw' in text or 'homework' in text:
                            content['homework'] = href
                
                if any(content.values()):  # 如果找到任何内容
                    content_links.append(content)
        
        return content_links

    async def crawl_url(self, url: str) -> None:
        """Crawl a specific URL for learning content."""
        logger.info(f"Crawling URL for learning content: {url}")
        print(f"🕷️ 开始爬取URL: {url}")
        
        try:
            # 创建下载目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            download_dir = os.path.join(self._scraping_config.download_directory, f'crawl_results_{timestamp}')
            os.makedirs(download_dir, exist_ok=True)
            
            # 发送请求获取页面内容
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 解析页面内容
            content_links = self._extract_course_content(response.text, url)
            
            print(f"\n✅ 页面解析完成!")
            print(f"🔍 发现 {len(content_links)} 个课程内容项")
            
            # 保存课程内容结构
            structure_file = os.path.join(download_dir, 'course_structure.json')
            with open(structure_file, 'w', encoding='utf-8') as f:
                json.dump(content_links, f, indent=2, ensure_ascii=False)
            
            print("\n📥 开始下载课程资源...")
            
            video_count = 0
            pdf_count = 0
            ppt_count = 0
            
            # 下载每个内容项的资源
            for content in content_links:
                print(f"\n🔍 处理主题: {content['topic']}")
                
                # 下载PDF
                if content['pdf']:
                    print(f"📄 下载PDF: {content['pdf']}")
                    try:
                        self._download_file(content['pdf'], download_dir)
                        pdf_count += 1
                    except Exception as e:
                        print(f"❌ PDF下载失败: {str(e)}")
                
                # 下载PPT
                if content['ppt']:
                    print(f"📊 下载PPT: {content['ppt']}")
                    try:
                        self._download_file(content['ppt'], download_dir)
                        ppt_count += 1
                    except Exception as e:
                        print(f"❌ PPT下载失败: {str(e)}")
                
                # 下载视频
                if content['video']:
                    print(f"📺 下载视频: {content['video']}")
                    try:
                        await self._download_video_with_transcript(content['video'], download_dir)
                        video_count += 1
                    except Exception as e:
                        print(f"❌ 视频下载失败: {str(e)}")
            
            print(f"\n📊 下载统计:")
            print(f"📺 视频: {video_count} 个")
            print(f"📄 PDF: {pdf_count} 个")
            print(f"📊 PPT: {ppt_count} 个")
            
            print(f"\n📊 爬取总结:")
            print(f"目标URL: {url}")
            print(f"课程结构保存在: {structure_file}")
            print(f"下载目录: {download_dir}")
            
        except Exception as e:
            logger.error(f"Error crawling URL: {e}")
            print(f"❌ 错误: {e}")

    async def _download_video_with_transcript(self, url: str, output_dir: str) -> None:
        """下载视频和字幕"""
        try:
            ydl_opts = {
                'format': 'best',  # 最佳质量
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'writesubtitles': True,  # 下载字幕
                'writeautomaticsub': True,  # 下载自动生成的字幕
                'subtitleslangs': ['en', 'zh-Hans', 'zh-Hant', 'zh-TW'],  # 下载英文和中文字幕
                'writedescription': True,  # 下载视频描述
                'writethumbnail': True,  # 下载缩略图
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [lambda d: print(
                    f"⏳ 下载中: {d['filename']}" if d['status'] == 'downloading' 
                    else f"✅ 完成: {d['filename']}" if d['status'] == 'finished' 
                    else '')],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_title = info.get('title', 'video')
                
                # 保存视频信息
                info_file = os.path.join(output_dir, f'{video_title}_info.json')
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'title': info.get('title'),
                        'description': info.get('description'),
                        'duration': info.get('duration'),
                        'view_count': info.get('view_count'),
                        'like_count': info.get('like_count'),
                        'upload_date': info.get('upload_date'),
                        'uploader': info.get('uploader'),
                        'channel_url': info.get('channel_url'),
                        'video_url': url,  # 新增：原始视频链接
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 视频信息已保存: {info_file}")
                
        except Exception as e:
            print(f"❌ 视频下载失败 {url}: {str(e)}")

    def _is_video_link(self, url: str) -> bool:
        """判断URL是否是视频链接。"""
        # 视频文件扩展名
        video_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm', '.mkv']
        # 视频平台域名和路径特征
        video_patterns = [
            'youtube.com/watch',
            'youtu.be/',  # 短链接
            'vimeo.com/',
            'bilibili.com/video',
            'b23.tv/'
        ]
        
        url_lower = url.lower()
        return (
            any(url_lower.endswith(ext) for ext in video_extensions) or
            any(pattern in url_lower for pattern in video_patterns) or
            'youtube' in url_lower  # 更宽松的 YouTube 链接匹配
        )

    def _is_downloadable_file(self, url: str) -> bool:
        """判断URL是否是可下载的文件。"""
        # 扩展可下载文件类型，包含 PPT
        downloadable_extensions = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.txt']
        return any(url.lower().endswith(ext) for ext in downloadable_extensions)

    def _extract_links_from_markdown(self, markdown: str, html: str, base_url: str) -> List[Tuple[str, str]]:
        """从Markdown和HTML内容中提取链接。"""
        from bs4 import BeautifulSoup
        links = []
        
        # 1. 从 HTML 提取链接（优先，因为更准确）
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a'):
            href = a.get('href')
            if href:
                text = a.get_text().strip()
                # 处理相对路径
                if not href.startswith(('http://', 'https://')):
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        parsed_base = urlparse(base_url)
                        href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                    else:
                        href = urljoin(base_url, href)
                links.append((text, href))
        
        # 2. 从 Markdown 提取链接（补充）
        markdown_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
        for match in markdown_pattern.finditer(markdown):
            text = match.group(1).strip()
            url = match.group(2).strip()
            if not url.startswith(('http://', 'https://')):
                url = urljoin(base_url, url)
            links.append((text, url))
        
        # 3. 提取直接的 URL（补充）
        url_pattern = re.compile(r'(?<![\(\[])(https?://[^\s\)\]]+)')
        for match in url_pattern.finditer(markdown):
            url = match.group(0)
            links.append(('', url))
        
        # 4. 去重，保留第一次出现的链接
        seen = set()
        unique_links = []
        for text, url in links:
            if url not in seen:
                seen.add(url)
                unique_links.append((text, url))
        
        return unique_links

    def _download_file(self, url: str, output_dir: str) -> None:
        """下载文件。"""
        try:
            
            # 更好的文件名提取
            parsed_url = urlparse(url)
            file_name = os.path.basename(unquote(parsed_url.path))
            
            # 如果没有文件名，尝试从URL中提取
            if not file_name or '.' not in file_name:
                file_name = url.split('/')[-1]
                if not file_name or '.' not in file_name:
                    file_name = f"downloaded_file_{int(time.time())}"
            
            file_path = os.path.join(output_dir, file_name)
            
            # 发送请求
            response = requests.get(url, stream=True, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 下载文件并显示进度
            with open(file_path, 'wb') as f, tqdm(
                desc=file_name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        size = f.write(chunk)
                        pbar.update(size)
            
            print(f"✅ 文件下载成功: {file_path}")
            
        except Exception as e:
            print(f"❌ 文件下载失败 {url}: {str(e)}")
            # 尝试重试一次
            try:
                print(f"🔄 重试下载: {url}")
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                
                file_name = url.split('/')[-1] if '/' in url else 'downloaded_file'
                file_path = os.path.join(output_dir, file_name)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ 重试成功: {file_path}")
            except Exception as retry_error:
                print(f"❌ 重试也失败: {str(retry_error)}")
    
    async def process_natural_language_command(self, command: str) -> None:
        """Process a natural language command for scraping operations."""
        logger.info(f"Processing command: {command}")
        
        try:
            if "search" in command.lower() or "find" in command.lower():
                topic = command.lower().replace("search", "").replace("find", "").strip()
                if topic:
                    await self.search_learning_resources(topic)
                else:
                    print("❓ Please specify a topic to search for")
            elif "crawl" in command.lower() or "http" in command.lower():
                words = command.split()
                url = next((word for word in words if word.startswith("http")), None)
                if url:
                    await self.crawl_url(url)
                else:
                    print("❓ Please provide a valid URL to crawl")
            else:
                print("❓ Command not recognized. Try 'search [topic]' or 'crawl [url]'")
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            print(f"❌ Error: {e}")
    
    @property
    def firecrawl_config(self) -> FirecrawlConfig:
        """Get the Firecrawl configuration."""
        return self._firecrawl_config
    
    @property
    def scraping_config(self) -> ScrapingConfig:
        """Get the scraping configuration."""
        return self._scraping_config


def create_scraping_application(
    firecrawl_config: Optional[FirecrawlConfig] = None,
    scraping_config: Optional[ScrapingConfig] = None,
    settings: Optional[Settings] = None
) -> ScrapingApplication:
    """Factory function to create a configured scraping application."""
    return ScrapingApplication(
        firecrawl_config=firecrawl_config,
        scraping_config=scraping_config,
        settings=settings
    )


async def main() -> None:
    """Main entry point for the scraping application."""
    try:
        parser = argparse.ArgumentParser(description="Learning Resource Scraper")
        parser.add_argument('--command', type=str, help='Natural language command for scraping')
        parser.add_argument('--topic', type=str, help='Topic to search for learning resources')
        parser.add_argument('--url', type=str, help='URL to crawl for content')
        args = parser.parse_args()
        
        # Create the scraping application
        app = create_scraping_application()
        
        print("=== Learning Resource Scraper ===")
        print(f"📁 Download directory: {app.scraping_config.download_directory}")
        print(f"🎯 Content types: {', '.join(app.scraping_config.content_types)}")
        print(f"🔧 Firecrawl server: {app.firecrawl_config.mcp_server_url}")
        print()
        
        if args.command:
            await app.process_natural_language_command(args.command)
        elif args.topic:
            await app.search_learning_resources(args.topic)
        elif args.url:
            await app.crawl_url(args.url)
        else:
            # Interactive mode
            print("🤖 Interactive mode - Enter commands:")
            print("   • search [topic] - Search for learning resources")
            print("   • crawl [url] - Crawl a specific URL")
            print("   • quit - Exit the application")
            print()
            
            while True:
                try:
                    command = input("scraper> ").strip()
                    if command.lower() in ['quit', 'exit', 'q']:
                        break
                    if command:
                        await app.process_natural_language_command(command)
                    print()
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
        
        print("✅ Scraping application completed successfully!")
        
    except Exception as e:
        logger.error(f"Scraping application failed: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Run the scraping application
    exit_code = asyncio.run(main())
    exit(exit_code)