import { useState } from 'react'
import { useNews } from '../hooks/useNews'
import { Header } from '../components/Header'
import { DateSelector } from '../components/DateSelector'
import { CategoryFilter } from '../components/CategoryFilter'
import { NewsList } from '../components/NewsList'
import { FileText, Loader2, ChevronUp, ChevronDown, ExternalLink } from 'lucide-react'

function safeSummaryTitle(titleZh: string): string {
  if (!titleZh) return titleZh
  const zhChars = (titleZh.match(/[\u4e00-\u9fff]/g) || []).length
  if (titleZh.split('\n').length > 2) return titleZh.split('\n')[0].trim()
  if (zhChars > 60) return titleZh.substring(0, 60) + '...'
  return titleZh
}

const categoryColors: Record<string, string> = {
  chip: '🔴 AI芯片动态',
  industry: '🔵 行业动态',
  tool: '🟢 工具与实战',
  academic: '🟣 学术精选',
}

export default function HomePage() {
  const {
    news,
    categories,
    selectedDate,
    actualDate,
    selectedCategory,
    setSelectedDate,
    setSelectedCategory,
    dailySummaryData,
    summaryLoading,
    generateDailySummary,
    loading,
    error,
    fetchNews,
  } = useNews()

  const [summaryCollapsed, setSummaryCollapsed] = useState(false)

  const handleGenerateSummary = () => {
    generateDailySummary()
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6 space-y-4">
          <DateSelector
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
          />
          <CategoryFilter
            categories={categories}
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
          />
        </div>

        <div className="mb-6">
          <button
            onClick={handleGenerateSummary}
            disabled={summaryLoading || !!dailySummaryData}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-base transition-all duration-200 ${
              dailySummaryData
                ? 'bg-green-100 text-green-800 cursor-default'
                : summaryLoading
                ? 'bg-gray-100 text-gray-400 cursor-wait'
                : 'bg-accent hover:bg-accent-hover text-white shadow-md hover:shadow-lg'
            }`}
          >
            {summaryLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>正在生成今日摘要...</span>
              </>
            ) : dailySummaryData ? (
              <>
                <FileText className="w-5 h-5" />
                <span>今日摘要已生成</span>
              </>
            ) : (
              <>
                <FileText className="w-5 h-5" />
                <span>生成今日新闻摘要</span>
              </>
            )}
          </button>
        </div>

        {dailySummaryData && (
          <div className="mb-6 bg-white rounded-lg shadow-md animate-fade-in">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-bold text-primary">📝 今日新闻摘要</h2>
              <button
                onClick={() => setSummaryCollapsed(!summaryCollapsed)}
                className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {summaryCollapsed ? (
                  <>
                    <span>展开</span>
                    <ChevronDown className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    <span>收起</span>
                    <ChevronUp className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
            {!summaryCollapsed && (
              <div className="p-4 space-y-4">
                {dailySummaryData.map((cat) => (
                  <div key={cat.category} className="space-y-2">
                    <h3 className="font-semibold text-gray-800 text-sm">
                      {categoryColors[cat.category] || cat.category_label}
                    </h3>
                    <ul className="space-y-2">
                      {cat.items.map((item, idx) => (
                      <li key={idx} className="text-sm text-gray-700 flex items-center gap-2">
                        <span className="text-gray-400 shrink-0">{idx + 1}.</span>
                        <span className="flex-1 truncate">{safeSummaryTitle(item.title_zh)}</span>
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-accent hover:underline text-xs shrink-0"
                        >
                          <span>原文链接</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </li>
                    ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {actualDate && actualDate !== selectedDate && (
          <div className="mb-4 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
            {selectedDate} 暂无新闻，已自动显示 {actualDate} 的新闻
          </div>
        )}

        <NewsList news={news} loading={loading} error={error} onRetry={fetchNews} />
      </main>

      <footer className="bg-primary text-white py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm">
          <p>LiveNews AI © 2026</p>
          <p className="text-gray-400 mt-1">每日AI新闻精选 · 完全免费</p>
        </div>
      </footer>
    </div>
  )
}
