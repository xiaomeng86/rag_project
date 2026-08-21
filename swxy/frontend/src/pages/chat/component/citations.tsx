import IconSearch from '@/assets/chat/search.svg'
import Markdown from '@/components/markdown'
import '@/components/markdown/index.scss'
import { Button, Drawer, Input } from 'antd'
import { useMemo, useState } from 'react'
import styles from './citations.module.scss'

function CitationsItem(props: {
  item: API.Reference
  onRead: () => void
}) {
  const { item, onRead } = props

  const content = useMemo(() => {
    const dom = document.createElement('div')
    dom.innerHTML = item.content
    return dom.innerText
  }, [item.content])

  return (
    <div className={styles['citations__item']}>
      <div className={styles['header']}>
        <div className={styles['name']} title={item.document_name}>
          {item.document_name}
        </div>
        <div className={styles['score']}>{item.citation_id}</div>
      </div>

      <div className={styles['desc']}>{content}</div>

      <div className={styles['footer']}>
        <div className={styles['footer-desc']}>
          页码 {item.positions?.[0]?.[0] ?? '-'}
        </div>
        <Button
          className={styles['footer-button']}
          color="primary"
          variant="solid"
          onClick={onRead}
        >
          阅读
        </Button>
      </div>
    </div>
  )
}

export default function Citations(props: { list?: API.Reference[] }) {
  const { list } = props

  const [read, setRead] = useState<API.Reference | null>(null)
  const [keyword, setKeyword] = useState('')
  const filteredList = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return list
    return list?.filter((item) =>
      `${item.document_name}\n${item.content}`.toLowerCase().includes(normalized),
    )
  }, [keyword, list])

  return (
    <div className={styles['citations']}>
      <div className={styles['citations__search']}>
        <Input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="搜索引文"
          suffix={<img src={IconSearch} alt="search" />}
        />
      </div>

      <div className={styles['citations__title']}>已选引文</div>

      <div className={styles['citations__list']}>
        {filteredList?.map((item) => (
          <CitationsItem
            key={item.chunk_id}
            item={item}
            onRead={() => setRead(item)}
          />
        ))}
      </div>

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
  )
}
