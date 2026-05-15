import { ExternalLink } from 'lucide-react'
import type { News } from '../types/news'
import { TrustBadge } from './TrustBadge'

interface NewsCardProps {
  news: News
}

const categoryColors: Record<string, string> = {
  chip: 'bg-chip',
  tool: 'bg-tool',
  industry: 'bg-industry',
  academic: 'bg-academic',
}

function cleanText(text: string): string {
  if (!text) return ''
  let cleaned = text
  cleaned = cleaned.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
  cleaned = cleaned.replace(/&#\d+;/g, '')
  cleaned = cleaned.replace(/&[a-zA-Z]+;/g, match => {
    const entities: Record<string, string> = {
      '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"',
      '&#8217;': "'", '&#8216;': "'", '&#8220;': '"', '&#8221;': '"',
      '&apos;': "'", '&nbsp;': ' ',
    }
    return entities[match] || match
  })
  cleaned = cleaned.replace(/\s{2,}/g, ' ')
  return cleaned.trim()
}

function formatParagraphs(text: string): string[] {
  const cleaned = cleanText(text)
  if (!cleaned) return []

  const existingParagraphs = cleaned.split(/\n{2,}/).filter(p => p.trim().length > 20)
  if (existingParagraphs.length > 1) {
    return existingParagraphs.map(p => p.trim())
  }

  let withMarkers = cleaned.replace(/([。！？])\s*/g, '$1\n')
  withMarkers = withMarkers.replace(/([.!?])\s+(?=[A-Z])/g, '$1\n')
  const rawSentences = withMarkers.split('\n').filter(s => s.trim())

  const paragraphs: string[] = []
  let current = ''

  for (const sentence of rawSentences) {
    current += (current ? ' ' : '') + sentence.trim()
    const endChar = current.trim().slice(-1)
    const isEndOfSentence = /[。！？\.!\?]/.test(endChar)
    const charCount = current.length

    if (isEndOfSentence && charCount > 80) {
      paragraphs.push(current.trim())
      current = ''
    } else if (charCount > 200) {
      paragraphs.push(current.trim())
      current = ''
    }
  }

  if (current.trim()) {
    paragraphs.push(current.trim())
  }

  return paragraphs.length > 0 ? paragraphs : [cleaned]
}

function isChineseSource(news: News): boolean {
  return news.title === news.title_zh
}

function isTitleHallucinated(title: string, titleZh: string): boolean {
  if (!title || !titleZh || title === titleZh) return false
  const zhChars = (titleZh.match(/[\u4e00-\u9fff]/g) || []).length
  const enWords = title.split(/\s+/).length
  if (enWords > 0 && zhChars > enWords * 4) return true
  if (titleZh.split('\n').length > 2) return true
  const listMarkerPattern = /(?:^|\n)\s*(?:[1-9][.)]|[•])\s/
  if (enWords < 10 && listMarkerPattern.test(titleZh)) return true
  return false
}

function getSafeTitleZh(news: News): string {
  if (isTitleHallucinated(news.title, news.title_zh)) {
    return news.title
  }
  return news.title_zh
}

export function NewsCard({ news }: NewsCardProps) {
  const publishedDate = news.published_at
    ? new Date(news.published_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    : ''

  const chineseSource = isChineseSource(news)
  const safeTitleZh = getSafeTitleZh(news)
  const originalParagraphs = formatParagraphs(news.original_text)
  const translatedParagraphs = formatParagraphs(news.translated_text || '')

  return (
    <div className="news-card overflow-hidden animate-fade-in">
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`${categoryColors[news.category] || 'bg-industry'} text-white text-xs px-2 py-1 rounded-full font-medium`}>
              {news.category_emoji} {news.category_label}
            </span>
            <TrustBadge
              trustLevel={news.trust_level}
              multiSourceVerified={news.multi_source_verified}
              aiWarning={news.ai_warning}
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>{news.source}</span>
            <span>·</span>
            <span>{publishedDate}</span>
          </div>
        </div>

        <h3 className="text-lg font-bold text-primary mb-1">{safeTitleZh}</h3>
        {!chineseSource && news.title !== safeTitleZh && (
          <p className="text-sm text-gray-600 italic">{news.title}</p>
        )}
      </div>

      {chineseSource ? (
        <div className="p-4">
          <div className="text-xs text-gray-500 mb-3 font-medium">原文内容</div>
          <div className="text-sm text-gray-700 leading-relaxed max-h-72 overflow-y-auto space-y-3">
            {originalParagraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-200">
          <div className="p-4 bg-gray-50">
            <div className="text-xs text-gray-500 mb-3 font-medium">English Original</div>
            <div className="text-sm text-gray-700 leading-relaxed max-h-72 overflow-y-auto space-y-3">
              {originalParagraphs.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </div>

          <div className="p-4">
            <div className="text-xs text-gray-500 mb-3 font-medium">中文翻译</div>
            <div className="text-sm text-gray-700 leading-relaxed max-h-72 overflow-y-auto space-y-3">
              {translatedParagraphs.length > 0 ? (
                translatedParagraphs.map((p, i) => (
                  <p key={i}>{p}</p>
                ))
              ) : (
                <p className="text-gray-400">翻译加载中...</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="px-4 py-3 flex items-center justify-end">
        <a
          href={news.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          <span>查看原文</span>
        </a>
      </div>
    </div>
  )
}
