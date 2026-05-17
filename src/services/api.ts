import axios from 'axios'
import type { NewsResponse, SummaryResponse } from '../types/news'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://livenews-ai-backend.onrender.com/api'

export const api = {
  getNews: async (date?: string, category?: string): Promise<NewsResponse> => {
    const params = new URLSearchParams()
    if (date) params.append('date', date)
    if (category && category !== 'all') params.append('category', category)

    const response = await axios.get<NewsResponse>(`${API_BASE_URL}/news?${params.toString()}`)
    return response.data
  },

  getDailySummary: async (date?: string): Promise<SummaryResponse> => {
    const params = new URLSearchParams()
    if (date) params.append('date', date)

    const response = await axios.post<SummaryResponse>(`${API_BASE_URL}/daily-summary?${params.toString()}`)
    return response.data
  },

  getCategories: async () => {
    const response = await axios.get(`${API_BASE_URL}/categories`)
    return response.data
  },
}
