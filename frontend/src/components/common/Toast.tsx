interface ToastProps {
  message: string
}

export function Toast({
  message,
}: ToastProps) {
  if (!message) {
    return null
  }

  return (
    <div
      className="toast"
      role="status"
      aria-live="polite"
    >
      {message}
    </div>
  )
}