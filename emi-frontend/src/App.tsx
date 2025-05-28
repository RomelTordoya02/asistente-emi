import { useState, useRef, useEffect } from "react"

const API_URL = import.meta.env.VITE_API_URL as string

interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: string
}

function App() {
  const [input, setInput] = useState<string>("")
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [currentTime, setCurrentTime] = useState<string>(getCurrentTime())

  // Función para obtener la hora actual formateada
  function getCurrentTime(): string {
    const now = new Date()
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }

  // Actualizar la hora cada minuto
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(getCurrentTime())
    }, 60000)

    return () => clearInterval(timer)
  }, [])

  // Auto-scroll al final cuando cambian los mensajes
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Enfocar el campo de entrada al cargar
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Función para formatear el contenido y resaltar "Según el artículo X del RAC-Y:"
  const formatMessage = (content: string) => {
    // Verificar si el mensaje contiene la estructura de un artículo RAC
    const racPattern = /Según el artículo \d+ del RAC-\d+/i;

    if (racPattern.test(content)) {
      // Extraer información del artículo
      const racMatch = content.match(/RAC-(\d+)/)
      const racNumber = racMatch ? racMatch[1] : ""
      const articleMatch = content.match(/artículo (\d+)/)
      const articleNumber = articleMatch ? articleMatch[1] : ""

      // Dividir el contenido en la parte del título y el resto
      const parts = content.split(new RegExp(`Según el artículo ${articleNumber} del RAC-${racNumber}`, 'i'))
      const beforeText = parts[0] || ""
      const afterText = parts.length > 1 ? parts[1] : ""

      return (
        <>
          {beforeText}
          <div className="mb-3">
            <h3 className="text-lg font-bold text-purple-300 mb-1">
              Según el artículo {articleNumber} del RAC-{racNumber}:
            </h3>
            <div className="text-cyan-100">{afterText}</div>
          </div>
        </>
      )
    }

    // Si no contiene la estructura de un artículo RAC, devolver el contenido sin formato
    return content
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()

    if (!input.trim()) return

    // Generar ID único para el mensaje
    const userMessageId = Date.now().toString()
    const messageTime = getCurrentTime()

    // Añadir mensaje del usuario al chat
    const userMessage: Message = {
      id: userMessageId,
      content: input,
      role: "user",
      timestamp: messageTime,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const response = await fetch(`${API_URL}/preguntar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pregunta: input }),
      })

      const data = await response.json()

      // Añadir respuesta del asistente al chat
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.respuesta || "❌ Error en la respuesta.",
        role: "assistant",
        timestamp: getCurrentTime(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error al conectar con el servidor:", error)

      // Añadir mensaje de error al chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "❌ No se pudo conectar con el servidor.",
        role: "assistant",
        timestamp: getCurrentTime(),
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-black text-white">
      {/* Header */}
      <header className="border-b border-purple-500/30 py-4 px-6 backdrop-blur-md bg-black/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse"></div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-500">
              Asistente EMI
            </h1>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-300">{currentTime}</span>
            <div className="hidden md:flex space-x-1">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="w-1.5 h-6 rounded-full bg-purple-500 opacity-70"
                  style={{ animationDelay: `${i * 0.2}s` }}
                ></div>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-500 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-5 max-w-md p-8 rounded-2xl backdrop-blur-lg bg-white/5 border border-white/10 shadow-xl">
              <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-r from-cyan-400 to-purple-500 flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-8 w-8 text-white"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-white">¡Bienvenido al Asistente EMI!</h2>
              <p className="text-gray-300">Escribe tu pregunta abajo para comenzar una conversación.</p>
              <div className="pt-4">
                <div className="flex justify-center space-x-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="w-2 h-2 rounded-full bg-purple-500"
                      style={{
                        animation: "pulse 1.5s infinite",
                        animationDelay: `${i * 0.2}s`,
                      }}
                    ></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"} items-start space-x-2`}
            >
              {message.role === "assistant" && (
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5 text-white"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M12 8V4m0 4 3 3m-3-3-3 3m3 7a9 9 0 1 1 0-18 9 9 0 0 1 0 18Z" />
                  </svg>
                </div>
              )}

              <div className={`flex flex-col ${message.role === "user" ? "items-end" : "items-start"} max-w-[80%]`}>
                <div
                  className={`rounded-2xl px-5 py-3.5 shadow-lg transition-all duration-300 ${message.role === "user"
                      ? "bg-gradient-to-r from-blue-600 to-indigo-700 text-white"
                      : "backdrop-blur-md bg-white/10 border border-white/10 text-white"
                    }`}
                >
                  <div className="whitespace-pre-wrap text-left">
                    {message.role === "assistant" ? formatMessage(message.content) : message.content}
                  </div>
                </div>
                <span className="text-xs text-gray-400 mt-1 px-2">{message.timestamp}</span>
              </div>

              {message.role === "user" && (
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5 text-white"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex justify-start items-start space-x-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 8V4m0 4 3 3m-3-3-3 3m3 7a9 9 0 1 1 0-18 9 9 0 0 1 0 18Z" />
              </svg>
            </div>
            <div className="backdrop-blur-md bg-white/10 border border-white/10 rounded-2xl px-5 py-3.5 flex items-center space-x-3">
              <div className="flex space-x-1">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 rounded-full bg-cyan-400"
                    style={{
                      animation: "bounce 1.4s infinite ease-in-out",
                      animationDelay: `${i * 0.15}s`,
                    }}
                  ></div>
                ))}
              </div>
              <p className="text-gray-300">Procesando respuesta...</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-purple-500/30 p-4 backdrop-blur-md bg-black/30">
        <form onSubmit={handleSubmit} className="flex space-x-3 max-w-4xl mx-auto">
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu pregunta..."
              className="min-h-[60px] w-full resize-none rounded-xl border border-purple-500/50 bg-white/5 backdrop-blur-sm p-4 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-all duration-300"
              rows={1}
              style={{ maxHeight: "150px" }}
            />
            <div className="absolute inset-0 rounded-xl pointer-events-none border border-purple-500/20 bg-gradient-to-r from-cyan-500/5 to-purple-500/5"></div>
          </div>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="h-[60px] w-[60px] rounded-xl bg-gradient-to-r from-cyan-500 to-purple-600 text-white flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-purple-500/20 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-all duration-300 group"
          >
            {isLoading ? (
              <svg className="animate-spin h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 transform group-hover:translate-x-1 transition-transform duration-300"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

export default App