declare namespace API {
  interface Repository {
    document_id: string
    file_name: string
    document_type: string
    file_size: number
    status: 'processing' | 'ready'
    chunk_count: number
    created_at: string
    updated_at: string
  }
}
