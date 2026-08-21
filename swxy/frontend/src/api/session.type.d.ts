declare namespace API {
  interface Session {
    created_at: string
    session_id: string
    session_name: string
    updated_at: string
  }

  interface Message {
    message_id: string
    session_id: string
    user_question: string
    model_answer: string
    thinking: string | null
    citations: Reference[]
    recommendations: string[]
    created_at: string
  }

  interface ChatItem {
    id: number
    role: import('@/configs').ChatRole
    type: import('@/configs').ChatType
    loading?: boolean
    error?: string
    content?: string
    think?: string
    documents?: Document[]
    reference?: Reference[]
    recommended_questions?: string[]
  }

  interface Document {
    document_id: string
    document_name: string
    content: string
  }

  interface Reference {
    citation_id: number
    chunk_id: string
    document_id: string
    document_name: string
    content: string
    score: number | null
    positions: number[][]
  }

  interface TemporaryDocument {
    document_id: string
    document_name: string
    document_type: string
    file_size: number
    expires_in_seconds: number
  }
}
