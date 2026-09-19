import {
  ImagePlus,
  Sparkles,
} from 'lucide-react'

import {
  useEffect,
  useState,
} from 'react'

import { Avatar } from '../components/common/Avatar'

import type {
  User,
} from '../types/index'

export interface CreatePostDraft {
  postId: string
  caption: string
  imageFile: File
}

interface CreatePostPageProps {
  currentUser: User

  onPublish: (
    draft: CreatePostDraft,
  ) => Promise<void>
}

export function CreatePostPage({
  currentUser,
  onPublish,
}: CreatePostPageProps) {
  const [postId, setPostId] = useState(() => `post-user-${crypto.randomUUID()}`)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [
    caption,
    setCaption,
  ] = useState('')

  const [
    imageFile,
    setImageFile,
  ] =
    useState<File | null>(
      null,
    )

  const [
    previewUrl,
    setPreviewUrl,
  ] = useState<
    string | null
  >(null)

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(
          previewUrl,
        )
      }
    }
  }, [previewUrl])

  function handleImage(
    file?: File,
  ) {
    if (!file) {
      return
    }

    if (previewUrl) {
      URL.revokeObjectURL(
        previewUrl,
      )
    }

    const nextUrl =
      URL.createObjectURL(
        file,
      )

    setImageFile(file)
    setPreviewUrl(nextUrl)
  }

  async function handlePublish() {
    if (!imageFile) {
      return
    }

    setSaving(true)
    setError('')
    try {
    await onPublish({
      postId,
      caption:
        caption.trim(),
      imageFile,
    })

    setCaption('')
    setImageFile(null)

    if (previewUrl) {
      URL.revokeObjectURL(
        previewUrl,
      )
    }

    setPreviewUrl(null)
    setPostId(`post-user-${crypto.randomUUID()}`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '發布失敗，請重試')
    } finally { setSaving(false) }
  }

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">
            NEW OOTD
          </span>

          <h1>
            分享今天的穿搭。
          </h1>

          <p>
            上傳照片後，AI
            將自動辨識單品、風格與場合。
          </p>
        </div>
      </div>

      <div className="post-composer">
        <label className="upload-box">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="穿搭貼文預覽"
            />
          ) : (
            <div>
              <ImagePlus
                size={36}
                strokeWidth={
                  1.4
                }
              />

              <strong>
                選擇穿搭照片
              </strong>

              <span>
                JPG、PNG、WEBP
              </span>
            </div>
          )}

          <input
            type="file"
            accept="image/*"
            onChange={
              event =>
                handleImage(
                  event
                    .target
                    .files?.[0],
                )
            }
          />
        </label>

        <div className="post-fields">
          <div className="user-row">
            <Avatar
              user={
                currentUser
              }
              size="small"
            />

            <div>
              <strong>
                {
                  currentUser
                    .displayName
                }
              </strong>

              <small>
                @
                {
                  currentUser
                    .username
                }
              </small>
            </div>
          </div>

          <textarea
            value={caption}
            maxLength={500}
            rows={6}
            placeholder="說說今天的穿搭..."
            onChange={
              event =>
                setCaption(
                  event
                    .target
                    .value,
                )
            }
          />

          <div className="ai-tag-preview">
            <Sparkles
              size={17}
            />

            <div>
              <strong>
                AI Auto Tag
              </strong>

              <span>
                發布後自動辨識
                Style、Color、
                Occasion 與 Clothing
                Items
              </span>
            </div>
          </div>

          <button
            type="button"
            className="primary-button"
            disabled={
              !imageFile || saving
            }
            onClick={
              handlePublish
            }
          >
            {saving ? '發布中...' : '發布穿搭'}
          </button>
          {error && <div className="form-error" role="alert">{error}</div>}
        </div>
      </div>
    </section>
  )
}
