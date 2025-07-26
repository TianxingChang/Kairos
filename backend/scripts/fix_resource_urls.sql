-- 修复无效的resource_url路径
-- 将本地文件路径替换为可访问的网络资源或占位符

-- 针对具体的资源进行修复
UPDATE ai.learning_resource 
SET resource_url = 'https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/'
WHERE id = 1 AND title LIKE '%MIT线性代数%';

UPDATE ai.learning_resource 
SET resource_url = 'https://docs.python.org/zh-cn/3/'
WHERE id = 2 AND title LIKE '%Python%';

UPDATE ai.learning_resource 
SET resource_url = 'https://www.coursera.org/learn/machine-learning'
WHERE id = 3 AND title LIKE '%机器学习%';

UPDATE ai.learning_resource 
SET resource_url = 'https://www.deeplearning.ai/courses/deep-learning-specialization/'
WHERE id = 4 AND title LIKE '%深度学习%';

UPDATE ai.learning_resource 
SET resource_url = 'https://arxiv.org/abs/1706.03762'
WHERE id = 5 AND title LIKE '%Transformer%';

UPDATE ai.learning_resource 
SET resource_url = 'https://cs231n.github.io/convolutional-networks/'
WHERE id = 6 AND title LIKE '%CNN%';

-- 对于其他包含本地路径的资源，根据资源类型设置合适的占位符或示例URL
UPDATE ai.learning_resource 
SET resource_url = CASE 
    WHEN resource_type = 'video' THEN 'https://www.youtube.com/placeholder-video-id'
    WHEN resource_type = 'document' THEN 'https://example.com/docs/placeholder.pdf'
    WHEN resource_type = 'url' THEN 'https://example.com/resource'
    WHEN resource_type = 'presentation' THEN 'https://example.com/presentations/placeholder.pptx'
    ELSE 'https://example.com/resource'
END
WHERE resource_url LIKE '/Users/%' OR resource_url LIKE 'file://%';

-- 添加一个注释字段来标记这些URL需要后续更新
ALTER TABLE ai.learning_resource ADD COLUMN IF NOT EXISTS url_needs_update BOOLEAN DEFAULT FALSE;

-- 标记需要更新的URL
UPDATE ai.learning_resource 
SET url_needs_update = TRUE 
WHERE resource_url LIKE 'https://example.com/%' OR resource_url LIKE '%placeholder%';

-- 为常见的学习资源类型提供更好的默认URL
UPDATE ai.learning_resource 
SET resource_url = 'https://www.khanacademy.org/math/linear-algebra',
    url_needs_update = FALSE
WHERE id = 7 AND title LIKE '%线性代数%PDF%';

UPDATE ai.learning_resource 
SET resource_url = 'https://www.coursera.org/learn/probability-theory-foundation-for-data-science',
    url_needs_update = FALSE
WHERE id = 8 AND title LIKE '%概率论%';

UPDATE ai.learning_resource 
SET resource_url = 'https://spinningup.openai.com/en/latest/',
    url_needs_update = FALSE
WHERE id = 9 AND title LIKE '%强化学习%';

UPDATE ai.learning_resource 
SET resource_url = 'https://jalammar.github.io/illustrated-transformer/',
    url_needs_update = FALSE
WHERE id = 10 AND title LIKE '%Attention%' OR title LIKE '%注意力%';

COMMIT;