import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(options?: AxiosRequestConfig) {
  return request.get<API.Repository[]>('/knowledge/documents', options)
}

export function upload(params: { file: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('file', params.file)
  return request.post<API.Repository>('/knowledge/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...options,
  })
}

export function remove(
  params: { document_id: string },
  options?: AxiosRequestConfig,
) {
  return request.delete<{
    document_id: string
    deleted_chunks: number
    message: string
  }>(`/knowledge/documents/${encodeURIComponent(params.document_id)}`, options)
}
