import { useState, useEffect, useCallback } from 'react'
import type { News, Category, SummaryCategory } from '../types/news'
import { api } from '../services/api'

const getChinaDate = (): string => {
  const now = new Date()
  const offset = 8 * 60
  const utc = now.getTime() + now.getTimezoneOffset() * 60000
  const chinaTime = new Date(utc + offset * 60000)
  return chinaTime.toISOString().split('T')[0]
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() - 1)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function useNews() {
  const [news, setNews] = useState<News[]>([])
  const [categories] = useState<Category[]>([
    { value: 'all', label: '全部', emoji: '📋' },
    { value: 'chip', label: 'AI芯片动态', emoji: '🔴' },
    { value: 'tool', label: '工具与实战', emoji: '🟢' },
    { value: 'industry', label: '行业动态', emoji: '🔵' },
    { value: 'academic', label: '学术精选', emoji: '🟣' },
  ])
  const [selectedDate, setSelectedDate] = useState(getChinaDate)
  const [actualDate, setActualDate] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dailySummaryData, setDailySummaryData] = useState<SummaryCategory[] | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)

  const fetchNews = useCallback(async () => {
    setLoading(true)
    setError(null)
    setActualDate(null)
    try {
      const today = getChinaDate()
      let response = await api.getNews(selectedDate, selectedCategory)

      if (response.data.news.length === 0 && selectedDate !== today) {
        response = await api.getNews(today, selectedCategory)
        if (response.data.news.length > 0) {
          setActualDate(response.data.date)
        }
      }

      if (response.data.news.length === 0 && selectedCategory && selectedCategory !== 'all') {
        const todayResp = await api.getNews(today)
        if (todayResp.data.news.length > 0) {
          setActualDate(todayResp.data.date)
          response = todayResp
        }
      }

      setNews(response.data.news)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取新闻失败')
    } finally {
      setLoading(false)
    }
  }, [selectedDate, selectedCategory])

  const generateDailySummary = async () => {
    if (summaryLoading || dailySummaryData) return
    setSummaryLoading(true)
    try {
      const response = await api.getDailySummary(selectedDate)
      if (response.success) {
        setDailySummaryData(response.data.summary_data)
      }
    } catch {
      // ignore
    } finally {
      setSummaryLoading(false)
    }
  }

  useEffect(() => {
    fetchNews()
  }, [fetchNews])

  useEffect(() => {
    setDailySummaryData(null)
  }, [selectedDate])

  return {
    news,
    categories,
    selectedDate,
    actualDate,
    selectedCategory,
    loading,
    error,
    dailySummaryData,
    summaryLoading,
    setSelectedDate,
    setSelectedCategory,
    generateDailySummary,
    fetchNews,
  }
}
