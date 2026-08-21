import * as api from '@/api'
import IconDelete from '@/assets/repository/action/delete.svg'
import IconSearch from '@/assets/repository/search.svg'
import { PlusOutlined } from '@ant-design/icons'
import { useRequest } from 'ahooks'
import { Button, Input, Modal, Popconfirm, Table } from 'antd'
import { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useMemo, useRef, useState } from 'react'
import { FileIcon } from './components/file-icon'
import { Status } from './components/status'
import RepositoryUpload, { RepositoryUploadRef } from './components/upload'
import styles from './index.module.scss'

type IRepository = API.Repository & {
  $suffix: FileIcon
  method: string
}

export default function Index() {
  const { data, refresh } = useRequest(async () => {
    const { data } = await api.repository.list()
    return data?.map(
      (item) =>
        ({
          ...item,
          $suffix: item.file_name.split('.').pop() as FileIcon,
          method: '自动解析 / 128 Token',
        }) satisfies IRepository,
    )
  })

  const columns = useMemo<ColumnsType<IRepository>>(
    () => [
      {
        title: '文件名',
        dataIndex: 'file_name',
        width: 200,
        render(value, row) {
          return (
            <div className={styles['repository-page__file-name']} title={value}>
              <FileIcon className={styles['icon']} suffix={row.$suffix} />
              {value}
            </div>
          )
        },
      },
      {
        title: '切片数量',
        dataIndex: 'chunk_count',
        width: 100,
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        width: 200,
        render(value) {
          return dayjs(value).format('MM/DD/YYYY HH:mm:ss')
        },
      },
      {
        title: '切片方式',
        dataIndex: 'method',
        width: 100,
      },
      {
        title: '状态',
        dataIndex: 'status',
        width: 100,
        render(value) {
          return <Status status={value} />
        },
      },
      {
        title: '操作',
        dataIndex: 'action',
        width: 100,
        render(_, row) {
          return (
            <Popconfirm
              title="确定要删除该文件吗？"
              onConfirm={async () => {
                await api.repository.remove({
                  document_id: row.document_id,
                })
                refresh()
              }}
            >
              <Button
                color="default"
                variant="text"
                shape="circle"
                size="small"
              >
                <img src={IconDelete} />
              </Button>
            </Popconfirm>
          )
        },
      },
    ],
    [refresh],
  )
  const scroll = useMemo(() => {
    return {
      x: columns?.reduce((prev, current) => {
        return prev + parseInt(String(current.width ?? 0))
      }, 0),
    }
  }, [columns])

  const [keyword, setKeyword] = useState('')
  const filteredData = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return data
    return data?.filter((item) =>
      item.file_name.toLowerCase().includes(normalized),
    )
  }, [data, keyword])

  /* 上传 */
  const [openUpload, setOpenUpload] = useState(false)
  const uploadRef = useRef<RepositoryUploadRef>(null)
  const [uploading, setUploading] = useState(false)

  return (
    <div className={styles['repository-page']}>
      <div className={styles['repository-page__header']}>
        <div className={styles['title']}>知识库</div>
        <div className={styles['desc']}>
          在开始AI对话之前，请等待文档解析完成。
        </div>
      </div>

      <div className={styles['repository-page__body']}>
        <div className={styles['header']}>
          <Input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索文件"
            prefix={<img src={IconSearch} />}
            style={{ width: 210 }}
          />

          <Button type="primary" onClick={() => setOpenUpload(true)}>
            <PlusOutlined />
            添加文档
          </Button>
        </div>

        <Table<IRepository>
          rowKey="document_id"
          columns={columns}
          dataSource={filteredData}
          scroll={scroll}
          pagination={false}
        />
      </div>

      <Modal
        title="上传文档"
        open={openUpload}
        width={400}
        destroyOnClose
        onCancel={() => {
          if (uploading) return
          setOpenUpload(false)
        }}
        onOk={async () => {
          setUploading(true)
          try {
            await uploadRef.current?.submit()
            setOpenUpload(false)
            refresh()
          } finally {
            setUploading(false)
          }
        }}
      >
        <RepositoryUpload beforeUpload={() => false} ref={uploadRef} />
      </Modal>
    </div>
  )
}
