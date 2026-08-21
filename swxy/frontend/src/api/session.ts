import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(options?: AxiosRequestConfig) {
  return request.get<{ sessions: API.Session[] }>('/sessions', options)
}

export function detail(
  params: { session_id: string },
  options?: AxiosRequestConfig,
) {
  return request.get<API.Message[]>(
    `/sessions/${encodeURIComponent(params.session_id)}/messages`,
    options,
  )
}

export function create(options?: AxiosRequestConfig) {
  return request.post<API.Session>('/sessions', undefined, options)
}

export function chat(
  params: { id: string; message: string },
  options?: AxiosRequestConfig,
) {
  return request.post<ReadableStream>(
    `/sessions/${encodeURIComponent(params.id)}/chat`,
    { message: params.message },
    {
      headers: { Accept: 'text/event-stream' },
      responseType: 'stream',
      adapter: 'fetch',
      loading: false,
      ...options,
    },
  )
}

export function putTemporaryDocument(
  params: { session_id: string; file: File },
  options?: AxiosRequestConfig,
) {
  const form = new FormData()
  form.append('file', params.file)
  return request.put<API.TemporaryDocument>(
    `/sessions/${encodeURIComponent(params.session_id)}/temporary-document`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' }, ...options },
  )
}

export function documents(
  params: { session_id: string },
  options?: AxiosRequestConfig,
) {
  return request.get<{
    session_id: string
    has_document: boolean
    document: API.TemporaryDocument | null
  }>(`/sessions/${encodeURIComponent(params.session_id)}/documents`, options)
}
