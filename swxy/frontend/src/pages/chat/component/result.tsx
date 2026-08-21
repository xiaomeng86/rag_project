import IconCopy from '@/assets/chat/copy.svg'
import IconShare from '@/assets/chat/share.svg'
import Markdown from '@/components/markdown'
import { ArrowRightOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import classNames from 'classnames'
import dayjs from 'dayjs'
import { TokenizerAndRendererExtension } from 'marked'
import { useCallback, useMemo } from 'react'
import styles from './result.module.scss'

export function Result(props: {
  item: API.ChatItem
  isEnd?: boolean
  onSend?: (text: string) => void
  onRefrence?: (index: number) => void
}) {
  const { item, isEnd, onSend, onRefrence } = props

  /* markdown */
  const extensions = useMemo<TokenizerAndRendererExtension[]>(
    () => [
      {
        name: 'reference',
        level: 'inline',
        start(src) {
          return src.match(/##\d+\$\$/)?.index
        },
        tokenizer(src) {
          const match = /^##(\d+?)\$\$/.exec(src)
          if (match) {
            const [raw, index] = match
            return {
              type: 'reference',
              raw,
              index: this.lexer.inlineTokens(index),
              tokens: [],
            }
          }
        },
        renderer(token) {
          const index = this.parser.parseInline(token.index)
          return `<span class="refrence-token" data-refrence-index="${index}">[${Number(index)}]</span>`
        },
      },
    ],
    [],
  )

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement
      const index = target.getAttribute('data-refrence-index')
      if (index) {
        onRefrence?.(Number(index))
      }
    },
    [onRefrence],
  )

  return (
    <div className={styles['chat-message-result']}>
      {item.think ? (
        <Markdown
          className={classNames(
            styles['chat-message-result__think'],
            styles['chat-message-result__md'],
          )}
          value={item.think}
          extensions={extensions}
          onClick={handleClick}
        />
      ) : null}

      {item.content ? (
        <Markdown
          className={styles['chat-message-result__md']}
          value={item.content}
          extensions={extensions}
          onClick={handleClick}
        />
      ) : null}

      {item.error ? (
        <div className={styles['chat-message-result__error']}>{item.error}</div>
      ) : null}

      {item.loading ? null : (
        <>
          <div className={styles['chat-message-result__actions']}>
            <div className={styles['date']}>
              {dayjs().format('HH:mm YYYY/MM/DD')}
            </div>

            <Button
              variant="text"
              color="primary"
              shape="circle"
              size="small"
              title="复制回答"
              style={{ color: 'var(--ant-color-primary)' }}
              onClick={async () => {
                await navigator.clipboard.writeText(item.content ?? '')
                window.$app.message.success('已复制')
              }}
            >
              <img src={IconCopy} />
            </Button>

            <Button
              variant="text"
              color="primary"
              shape="circle"
              size="small"
              title="导出为 TXT"
              style={{ color: 'var(--ant-color-primary)' }}
              onClick={() => {
                const url = `data:text/plain;charset=utf-8,${encodeURIComponent(item.content ?? '')}`
                const anchor = document.createElement('a')
                anchor.href = url
                anchor.download = 'gsk-poc-answer.txt'
                anchor.click()
              }}
            >
              <img src={IconShare} />
            </Button>
          </div>

          {isEnd ? (
            <div className={styles['chat-message-result__quick-reply']}>
              {item.recommended_questions?.map((item) => (
                <Button
                  className={styles['item']}
                  key={item}
                  onClick={() => onSend?.(item)}
                >
                  <span className={styles['text']}>🔎 {item}</span>
                  <ArrowRightOutlined className={styles['arrow']} />
                </Button>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}
