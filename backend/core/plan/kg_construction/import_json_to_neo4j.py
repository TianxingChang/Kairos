#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：将知识图谱 JSON 文件直接导入 Neo4j 数据库。
用法：
    python scripts/import_json_to_neo4j.py <json文件路径> [neo4j连接uri] [用户名] [密码]
    
    - json文件路径：知识图谱的json文件，默认为 data/reinforcement_learning_hardcoded.json
    - neo4j连接uri：如 bolt://localhost:7687，默认为 bolt://localhost:7687
    - 用户名/密码：默认为 neo4j/12345678

示例：
    python scripts/import_json_to_neo4j.py data/my_graph.json bolt://localhost:7687 neo4j mypassword

"""

import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
    import json
except ImportError:
    print("❌ 需要安装neo4j库: pip install neo4j")
    sys.exit(1)

def import_data():
    """直接导入数据"""
    
    print("🔄 开始导入知识图谱数据到Neo4j")
    print("=" * 50)
    
    # 连接参数
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "12345678"
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        print("✅ Neo4j连接成功!")
        
        with driver.session() as session:
            # 1. 清理现有数据
            print("🧹 清理现有数据...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 2. 创建约束
            print("🔧 创建唯一性约束...")
            session.run("CREATE CONSTRAINT knowledge_node_id IF NOT EXISTS FOR (n:KnowledgeNode) REQUIRE n.id IS UNIQUE")
            
            # 3. 加载JSON数据
            json_file = Path(__file__).parent.parent / "data" / "reinforcement_learning_hardcoded.json"
            
            with open(json_file, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            print(f"📊 加载数据: {graph_data['name']}")
            print(f"   节点: {len(graph_data['nodes'])}")
            print(f"   边: {len(graph_data['edges'])}")
            
            # 4. 创建节点
            print("📝 创建节点...")
            for i, node in enumerate(graph_data['nodes']):
                cypher = """
                CREATE (n:KnowledgeNode {
                    id: $id,
                    label: $label,
                    category: $category,
                    description: $description,
                    estimatedHours: $estimatedHours
                })
                """
                
                params = {
                    'id': node['id'],
                    'label': node['label'],
                    'category': node['category'],
                    'description': node['description'],
                    'estimatedHours': node.get('estimatedHours', 1)
                }
                
                # Add importance if exists
                if 'importance' in node:
                    cypher = """
                    CREATE (n:KnowledgeNode {
                        id: $id,
                        label: $label,
                        category: $category,
                        description: $description,
                        estimatedHours: $estimatedHours,
                        importance: $importance
                    })
                    """
                    params['importance'] = node['importance']
                
                session.run(cypher, params)
                
                if (i + 1) % 10 == 0:
                    print(f"   创建节点进度: {i + 1}/{len(graph_data['nodes'])}")
            
            print(f"✅ 成功创建 {len(graph_data['nodes'])} 个节点")
            
            # 5. 创建关系
            print("🔗 创建关系...")
            for i, edge in enumerate(graph_data['edges']):
                cypher = """
                MATCH (source:KnowledgeNode {id: $source_id})
                MATCH (target:KnowledgeNode {id: $target_id})
                CREATE (source)-[:PREREQUISITE_OF]->(target)
                """
                
                params = {
                    'source_id': edge['source'],
                    'target_id': edge['target']
                }
                
                session.run(cypher, params)
                
                if (i + 1) % 10 == 0:
                    print(f"   创建关系进度: {i + 1}/{len(graph_data['edges'])}")
            
            print(f"✅ 成功创建 {len(graph_data['edges'])} 个关系")
            
            # 6. 验证导入结果
            print("🔍 验证导入结果...")
            
            result = session.run("MATCH (n:KnowledgeNode) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]
            
            result = session.run("MATCH ()-[r:PREREQUISITE_OF]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            
            print(f"📊 导入完成:")
            print(f"   节点数量: {node_count}")
            print(f"   关系数量: {rel_count}")
            
            # 7. 显示一些示例数据
            print(f"\n📋 示例节点:")
            result = session.run("""
                MATCH (n:KnowledgeNode)
                RETURN n.id, n.label, n.category
                ORDER BY n.category, n.label
                LIMIT 5
            """)
            
            for record in result:
                print(f"   • {record['n.id']}: {record['n.label']} ({record['n.category']})")
            
            print(f"\n📋 示例关系:")
            result = session.run("""
                MATCH (source:KnowledgeNode)-[:PREREQUISITE_OF]->(target:KnowledgeNode)
                RETURN source.label, target.label
                LIMIT 5
            """)
            
            for record in result:
                print(f"   • {record['source.label']} → {record['target.label']}")
            
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def main():
    success = import_data()
    
    if success:
        print(f"\n🎉 知识图谱导入成功!")
        print(f"📋 验证方法:")
        print(f"1. 打开Neo4j Browser: http://localhost:7474")
        print(f"2. 运行查询: MATCH (n:KnowledgeNode)-[r]->(m) RETURN n,r,m LIMIT 25")
        print(f"3. 或者运行: MATCH (n:KnowledgeNode) WHERE n.category = '数学基础' RETURN n")
        return True
    else:
        print(f"\n❌ 导入失败，请检查错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)