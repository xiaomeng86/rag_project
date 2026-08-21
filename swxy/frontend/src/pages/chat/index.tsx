import * as api from '@/api'
import Markdown from '@/components/markdown'
import ComPageLayout from '@/components/page-layout'
import ComSender from '@/components/sender'
import { ChatRole, ChatType } from '@/configs'
import { deviceActions } from '@/store/device'
import { usePageTransport } from '@/utils'
import { useMount, useRequest, useUnmount } from 'ahooks'
import { Drawer } from 'antd'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { proxy, useSnapshot } from 'valtio'
import { sessionActions } from '../../store/session'
import ChatMessage from './component/chat-message'
import Citations from './component/citations'
import Contracts from './component/contracts'
import ChatDrawer from './component/drawer'
import Source from './component/source'
import styles from './index.module.scss'
import { createChatId, createChatIdText, transportToChatEnter } from './shared'

async function scrollToBottom() {
  await new Promise((resolve) => setTimeout(resolve))

  const threshold = 200
  const distanceToBottom =
    document.documentElement.scrollHeight -
    document.documentElement.scrollTop -
    document.documentElement.clientHeight

  if (distanceToBottom <= threshold) {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth',
    })
  }
}

export default function Index() {
  const { id } = useParams()
  const { data: ctx } = usePageTransport(transportToChatEnter)

  const [chat] = useState(() => {
    return proxy({
      list: [] as API.ChatItem[],
    })
  })
  const { list } = useSnapshot(chat) as { list: API.ChatItem[] }
  const [documents, setDocuments] = useState<API.Document[]>([])
  const [currentChatItem, setCurrentChatItem] = useState<API.ChatItem | null>(
    null,
  )

  const history = useRequest(
    async () => {
      const { data } = await api.session.detail({
        session_id: id!,
      })
      return data
    },
    {
      manual: true,
      onSuccess(data) {
        data.forEach((item) => {
          if (item.user_question) {
            chat.list.push({
              id: createChatId(),
              role: ChatRole.User,
              type: ChatType.Text,
              content: item.user_question,
            })
          }

          if (item.model_answer) {
            const map = new Map<string, API.Document>()
            const reference = item.citations ?? []
            const recommended_questions = item.recommendations ?? []

            reference?.forEach((chunk) => {
              map.set(chunk.document_id, {
                document_id: chunk.document_id,
                document_name: chunk.document_name,
                content: chunk.content,
              })
            })
            const documents = Array.from(map.values())

            chat.list.push({
              id: createChatId(),
              role: ChatRole.Assistant,
              type: ChatType.Document,
              content: item.model_answer,
              think: item.thinking ?? undefined,
              reference: reference,
              documents: documents?.length ? documents : undefined,
              recommended_questions: recommended_questions?.length
                ? recommended_questions
                : undefined,
            })
          }
        })

        setTimeout(() => {
          window.scrollTo({
            top: document.documentElement.scrollHeight,
          })
        })
      },
    },
  )

  const loading = useMemo(() => {
    return list.some((o) => o.loading) || history.loading
  }, [list, history.loading])
  const loadingRef = useRef(loading)
  loadingRef.current = loading
  useEffect(() => {
    deviceActions.setChatting(loading)
  }, [loading])
  useUnmount(() => {
    deviceActions.setChatting(false)
  })

  const sendChat = useCallback(
    async (target: API.ChatItem, message: string) => {
      setCurrentChatItem(target)
      target.loading = true
      try {
        //后端接口
        const res = await api.session.chat({
          id: id!,
          message,
        })
        sessionActions.updateKey()

        const reader = res.data.getReader()
        if (!reader) return

        await read(reader)
      } catch (error: any) {
        target.error = error?.message ?? 'Unknown error'
        throw error
      } finally {
        target.loading = false
      }

      async function read(reader: ReadableStreamDefaultReader<Uint8Array>) {
        let temp = ''
        const decoder = new TextDecoder('utf-8')
        while (true) {
          const { value, done } = await reader.read()
          temp += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')

          while (true) {
            const index = temp.indexOf('\n\n')
            if (index === -1) break

            const block = temp.slice(0, index)
            temp = temp.slice(index + 2)
            parseData(block)
            scrollToBottom()
          }

          if (done) {
            console.debug('数据接受完毕', temp)
            target.loading = false
            break
          }
        }
      }

      function parseData(block: string) {
        try {
          const data = block
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.replace(/^data:\s?/, ''))
            .join('\n')
          if (!data) return
          const json = JSON.parse(data)
          switch (json.type) {
            case 'thinking':
              target.think = `${target.think || ''}${json.content || ''}`
              break
            case 'answer':
              target.content = `${target.content || ''}${json.content || ''}`
              break
            case 'citations': {
              target.reference = json.citations ?? []

              const map = new Map<string, API.Document>()
              target.reference?.forEach((chunk) => {
                map.set(chunk.document_id, {
                  document_id: chunk.document_id,
                  document_name: chunk.document_name,
                  content: chunk.content,
                })
              })
              const nextDocuments = Array.from(map.values())
              target.documents = nextDocuments
              setDocuments(nextDocuments)
              break
            }
            case 'recommendations':
              target.recommended_questions = json.recommendations ?? []
              break
            case 'done':
              target.loading = false
              break
            case 'error':
              target.error = json.message || '问答处理失败'
              target.loading = false
              break
          }
        } catch {
          console.debug('解析失败')
          console.debug(block)
        }
      }
    },
    [id],
  )

  const send = useCallback(
    async (message: string) => {
      if (loadingRef.current) return
      if (!message) return

      if (chat.list.length === 0) {
        chat.list.push({
          id: createChatId(),
          role: ChatRole.User,
          type: ChatType.Text,
          content: message,
        })

        chat.list.push({
          id: createChatId(),
          role: ChatRole.Assistant,
          type: ChatType.Document,
          documents: [],
        })

        const target = chat.list[chat.list.length - 1]

        await sendChat(target, message!)
      } else {
        chat.list.push({
          id: createChatId(),
          role: ChatRole.User,
          type: ChatType.Text,
          content: message,
        })

        chat.list.push({
          id: createChatId(),
          role: ChatRole.Assistant,
          type: ChatType.Document,
          content: '',
        })
        scrollToBottom()

        const target = chat.list[chat.list.length - 1]

        await sendChat(target, message!)
      }
    },
    [chat, sendChat],
  )
  useMount(async () => {
    if (ctx?.data.message) {
      send(ctx.data.message)
    } else {
      history.run()
    }
  })

  useEffect(() => {
    const handleScroll = () => {
      const anchors: {
        id: string
        top: number
        item: API.ChatItem
      }[] = []

      chat.list
        .filter((o) => o.type === ChatType.Document)
        .forEach((item, index) => {
          const id = createChatIdText(item.id)
          const dom = document.getElementById(id)
          if (!dom) return

          const top = dom.offsetTop
          if (index === 0 || top < window.scrollY) {
            anchors.push({ id, top, item })
          }
        })

      if (anchors.length) {
        const current = anchors.reduce((prev, curr) =>
          curr.top > prev.top ? curr : prev,
        )

        setCurrentChatItem(current.item)
      }
    }

    window.addEventListener('scroll', handleScroll)

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [chat])

  const title = list[0]?.content ?? '新对话'

  const [read, setRead] = useState<API.Reference | null>(null)

  return (
    <ComPageLayout
      sender={
        <>
          {documents.length > 0 && <Source list={documents} />}
          <ComSender
            loading={loading}
            sessionId={id}
            onSend={send}
          />
        </>
      }
      right={
        <>
          {currentChatItem && currentChatItem.reference?.length ? (
            <ChatDrawer title="引文">
              <Citations list={currentChatItem.reference} />
            </ChatDrawer>
          ) : (
            <ChatDrawer title="文档">
              <Contracts list={documents} />
            </ChatDrawer>
          )}
        </>
      }
    >
      <div className={styles['chat-page']}>
        <div className={styles['chat-page__header']}>
          <div className={styles['chat-page__header-title']}>{title}</div>
        </div>

        <ChatMessage
          list={list}
          onSend={send}
          onOpenCiations={setCurrentChatItem}
          onRefrence={setRead}
        />

        <Drawer
          title={read?.document_name ?? ''}
          width={800}
          onClose={() => setRead(null)}
          open={!!read}
          destroyOnClose
        >
          <Markdown value={read?.content ?? ''} />
        </Drawer>
      </div>
    </ComPageLayout>
  )
}
