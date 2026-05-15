import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./news.db')

NEWS_SOURCES = {
    'openai': {
        'name': 'OpenAI Blog',
        'url': 'https://openai.com/blog/rss.xml',
        'type': 'rss',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 10,
        'content_type': 'official'
    },
    'deepmind': {
        'name': 'Google DeepMind',
        'url': 'https://deepmind.google/blog/rss.xml',
        'type': 'rss',
        'category': 'academic',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'official'
    },
    'google_ai': {
        'name': 'Google AI Blog',
        'url': 'https://blog.google/technology/ai/rss/',
        'type': 'rss',
        'category': 'industry',
        'trust_level': 'S',
        'priority': 8,
        'content_type': 'official'
    },
    'huggingface': {
        'name': 'Hugging Face Blog',
        'url': 'https://huggingface.co/blog/feed.xml',
        'type': 'rss',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'official'
    },
    'semianalysis': {
        'name': 'SemiAnalysis',
        'url': 'https://semianalysis.com/feed/',
        'type': 'rss',
        'category': 'chip',
        'trust_level': 'S',
        'priority': 10,
        'content_type': 'official'
    },
    'techcrunch_ai': {
        'name': 'TechCrunch AI',
        'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
        'type': 'rss',
        'category': 'industry',
        'trust_level': 'S',
        'priority': 6,
        'content_type': 'news'
    },
    'venturebeat_ai': {
        'name': 'VentureBeat AI',
        'url': 'https://venturebeat.com/category/ai/feed/',
        'type': 'rss',
        'category': 'industry',
        'trust_level': 'S',
        'priority': 6,
        'content_type': 'news'
    },
    'hackernews': {
        'name': 'Hacker News',
        'url': 'https://hnrss.org/frontpage',
        'type': 'rss',
        'category': 'industry',
        'trust_level': 'A',
        'priority': 5,
        'content_type': 'community'
    },
    'arxiv': {
        'name': 'ArXiv CS.AI',
        'url': 'http://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=15&sortBy=submittedDate&sortOrder=descending',
        'type': 'api',
        'category': 'academic',
        'trust_level': 'S',
        'priority': 7,
        'content_type': 'academic'
    },
    'qbitai': {
        'name': '量子位',
        'url': 'https://www.qbitai.com/feed',
        'type': 'rss',
        'category': 'industry',
        'trust_level': 'A',
        'priority': 5,
        'content_type': 'news_cn'
    },
    'mit_tr': {
        'name': 'MIT Tech Review',
        'url': 'https://www.technologyreview.com/feed/',
        'type': 'rss',
        'category': 'industry',
        'trust_level': 'S',
        'priority': 7,
        'content_type': 'news'
    },
    'github_trending': {
        'name': 'GitHub Trending AI',
        'url': 'https://github-trending-api.onrender.com/feeds/all/rss',
        'type': 'github_trending',
        'category': 'tool',
        'trust_level': 'A',
        'priority': 8,
        'content_type': 'community',
        'tags': ['ai', 'machine-learning', 'deep-learning', 'llm', 'gpt', 'neural-network']
    },
    'github_releases_llm': {
        'name': 'GitHub LLM Releases',
        'url': 'https://github.com/ollama/ollama/releases/feed.atom',
        'type': 'github_release',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'community'
    },
    'github_releases_lmstudio': {
        'name': 'GitHub LM Studio Releases',
        'url': 'https://github.com/lmstudio-am/lmstudio/releases/feed.atom',
        'type': 'github_release',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'community'
    },
    'github_releases_crewai': {
        'name': 'GitHub CrewAI Releases',
        'url': 'https://github.com/crewAIInc/crewAI/releases/feed.atom',
        'type': 'github_release',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'community'
    },
    'github_releases_langchain': {
        'name': 'GitHub LangChain Releases',
        'url': 'https://github.com/langchain-ai/langchain/releases/feed.atom',
        'type': 'github_release',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'community'
    },
    'github_releases_autogen': {
        'name': 'GitHub AutoGen Releases',
        'url': 'https://github.com/microsoft/autogen/releases/feed.atom',
        'type': 'github_release',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'community'
    },
    'reddit_localllama': {
        'name': 'Reddit LocalLLaMA',
        'url': 'https://www.reddit.com/r/LocalLLaMA/.rss',
        'type': 'reddit',
        'category': 'tool',
        'trust_level': 'A',
        'priority': 7,
        'content_type': 'community'
    },
    'reddit_ChatGPT': {
        'name': 'Reddit ChatGPT',
        'url': 'https://www.reddit.com/r/ChatGPT/.rss',
        'type': 'reddit',
        'category': 'tool',
        'trust_level': 'A',
        'priority': 6,
        'content_type': 'community'
    },
    'reddit_MachineLearning': {
        'name': 'Reddit MachineLearning',
        'url': 'https://www.reddit.com/r/MachineLearning/.rss',
        'type': 'reddit',
        'category': 'academic',
        'trust_level': 'A',
        'priority': 7,
        'content_type': 'community'
    },
    'youtube_yann_lecun': {
        'name': 'Yann LeCun YouTube',
        'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPbJo66M9qJmicbsCCWQQ',
        'type': 'youtube',
        'category': 'academic',
        'trust_level': 'S',
        'priority': 8,
        'content_type': 'video'
    },
    'youtube_sentdex': {
        'name': 'Sentdex Python/ML',
        'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=ZVxD6qbOedI2HQA',
        'type': 'youtube',
        'category': 'tool',
        'trust_level': 'A',
        'priority': 6,
        'content_type': 'video'
    },
    'blog_lilllog': {
        'name': "Lil'Log 博客",
        'url': 'https://lilianweng.github.io/rss.xml',
        'type': 'rss',
        'category': 'academic',
        'trust_level': 'S',
        'priority': 8,
        'content_type': 'blog'
    },
    'blog_e2eml': {
        'name': 'End-to-End ML',
        'url': 'https://e2eml.school/blog/rss.xml',
        'type': 'rss',
        'category': 'academic',
        'trust_level': 'A',
        'priority': 7,
        'content_type': 'blog'
    },
    'twitter_jimfan': {
        'name': 'Jim Fan Twitter/X',
        'url': 'https://nitter.privacydev.net/i/user/743112768825516032/rss',
        'type': 'twitter',
        'category': 'tool',
        'trust_level': 'A',
        'priority': 9,
        'content_type': 'social'
    },
    'twitter_karpathy': {
        'name': 'Andrej Karpathy Twitter/X',
        'url': 'https://nitter.privacydev.net/i/user/46020769/rss',
        'type': 'twitter',
        'category': 'tool',
        'trust_level': 'S',
        'priority': 10,
        'content_type': 'social'
    },
    'twitter_swyx': {
        'name': 'swyx Twitter/X',
        'url': 'https://nitter.privacydev.net/i/user/113385265/rss',
        'type': 'twitter',
        'category': 'industry',
        'trust_level': 'A',
        'priority': 8,
        'content_type': 'social'
    },
    'twitter_ylecun': {
        'name': 'Yann LeCun Twitter/X',
        'url': 'https://nitter.privacydev.net/i/user/2169293545/rss',
        'type': 'twitter',
        'category': 'academic',
        'trust_level': 'S',
        'priority': 9,
        'content_type': 'social'
    },
}

CATEGORY_CONFIG = {
    'chip': {
        'label': 'AI芯片动态',
        'emoji': '🔴',
        'keywords': ['chip', 'gpu', 'nvidia', 'amd', 'intel', 'huawei', '芯片', 'GPU', '算力',
                     'accelerator', 'semiconductor', 'tpu', 'npu', 'gaudi', 'blackwell',
                     'cerebras', 'wafer', 'fab', 'tsmc', '数据中心',
                     'colossus', 'groqchip', 'samba', 'tenstorrent', 'hbm', 'dram',
                     'silicon', 'asic', 'fpga', 'die bank', 'ramp',
                     'mi300', 'mi400', 'h200', 'b100', 'b200'],
        'strict_keywords': ['chip', 'gpu', 'nvidia', 'amd', 'intel', 'huawei', 'tsmc',
                           'semiconductor', 'tpu', 'npu', 'gaudi', 'blackwell', 'cerebras',
                           'hbm', 'silicon', 'asic', 'fpga', 'wafer', 'fab', 'accelerator']
    },
    'tool': {
        'label': '工具与实战',
        'emoji': '🟢',
        'keywords': ['copilot', 'chatgpt', 'claude', 'gemini', 'gpt', 'open source',
                    '开源', 'coding assistant', 'agent', 'mcp', 'rag', 'fine-tun',
                    'hugging face', 'api', 'sdk', 'framework',
                    'cursor', 'windsurf', 'codeium', 'v0', 'bolt', 'codex',
                    'model release', 'deploy', 'plugin', 'extension',
                    'ollama', 'lmstudio', 'crewai', 'langchain', 'autogen', 'vllm',
                    'local llm', 'self-hosted', 'quantization', 'lora', 'qlora',
                    'prompt engineering', 'vector database', 'embedding',
                    'multi-agent', 'agentic', 'workflow', 'automation',
                    'benchmark', 'performance', 'optimization', 'speed up',
                    'tutorial', 'guide', 'walkthrough', 'how to', 'tips', 'tricks',
                    'real-world', 'use case', 'case study', 'production', 'scale'],
        'strict_keywords': ['copilot', 'chatgpt', 'claude', 'gpt-4', 'gpt-5',
                           'open source', '开源', 'agent', 'mcp', 'rag',
                           'hugging face', 'api', 'sdk', 'framework', 'codex',
                           'ollama', 'lmstudio', 'crewai', 'langchain', 'autogen']
    },
    'industry': {
        'label': '行业动态',
        'emoji': '🔵',
        'keywords': ['funding', 'investment', '融资', '投资', 'ipo', 'acquisition',
                    'startup', 'revenue', 'market', 'regulation', 'policy',
                    '监管', '安全', 'openai', 'anthropic', 'deepmind', 'meta ai',
                    'microsoft ai', 'google ai', 'amazon ai', 'partnership',
                    'launches', 'announces', '发布', '合作', '融资',
                    'release notes', 'changelog', 'version', 'update'],
        'strict_keywords': ['funding', 'investment', 'ipo', 'acquisition', 'startup',
                           'revenue', 'regulation', 'policy', 'partnership']
    },
    'academic': {
        'label': '学术精选',
        'emoji': '🟣',
        'keywords': ['paper', 'research', 'study', 'arxiv', '论文', '研究', '学术',
                    'benchmark', 'neurips', 'icml', 'iclr',
                    'diffusion', 'reinforcement', 'multimodal', 'reasoning',
                    'embodied', 'robotics', 'autonomy',
                    'architecture', 'training', 'dataset', 'preprint'],
        'strict_keywords': ['paper', 'research', 'arxiv', '论文', '研究',
                           'benchmark', 'neurips', 'icml', 'iclr']
    }
}

NOISE_KEYWORDS = [
    'celebrity', 'gossip', 'movie', 'music', 'sport', 'fashion',
    'recipe', 'travel', 'horoscope', 'astrology', 'lottery',
    '明星', '八卦', '电影', '音乐', '体育', '时尚', '旅游',
    'beats solo', 'headphone', 'earbuds', 'purifier', 'vacuum',
    '耳机', '净化器', '吸尘器', '电动牙刷', '电动剃须刀',
    'crypto', 'bitcoin', 'nft', 'blockchain', '加密货币',
    'gaming chair', 'keyboard', 'mouse review',
]

MAX_DAILY_NEWS = 20
