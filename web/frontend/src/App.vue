<template>

  <div class="layout">

    <!-- Header -->

    <header class="header">

      <span class="logo">Кейн чучух</span>

      <button class="clear-btn" @click="clearChat" :disabled="messages.length === 0" title="Очистить диалог">

        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">

          <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>

        </svg>

      </button>

    </header>


    <!-- Messages -->

    <main class="messages" ref="messagesEl">

      <div v-if="messages.length === 0" class="empty">

        <p class="empty-title">Начните разговор</p>

        <p class="empty-sub">Напишите что-нибудь — и кейн ответит, отвчеаю</p>

      </div>


      <TransitionGroup name="msg" tag="div" class="messages-inner">

        <div

          v-for="msg in messages"

          :key="msg.id"

          class="bubble-wrap"

          :class="msg.role"

        >

          <div class="label">{{ msg.role === 'user' ? 'Вы' : 'ИИ' }}</div>

          <div class="bubble" v-html="renderText(msg.content)"></div>

        </div>

      </TransitionGroup>


      <!-- Typing indicator -->

      <Transition name="fade">

        <div v-if="loading" class="bubble-wrap assistant">

          <div class="label">ИИ</div>

          <div class="bubble typing">

            <span></span><span></span><span></span>

          </div>

        </div>

      </Transition>


      <!-- Error -->

      <Transition name="fade">

        <div v-if="error" class="error-msg">

          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">

            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>

          </svg>

          {{ error }}

        </div>

      </Transition>

    </main>


    <!-- Input -->

    <footer class="input-area">

      <div class="input-wrap">

        <textarea

          ref="inputEl"

          v-model="draft"

          placeholder="Напишите сообщение…"

          rows="1"

          :disabled="loading"

          @keydown.enter.exact.prevent="send"

          @keydown.enter.shift.exact="newline"

          @input="autoResize"

        ></textarea>

        <button class="send-btn" @click="send" :disabled="loading || !draft.trim()" aria-label="Отправить">

          <svg v-if="!loading" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">

            <line x1="22" y1="2" x2="11" y2="13"/>

            <polygon points="22 2 15 22 11 13 2 9 22 2"/>

          </svg>

          <span v-else class="spin"></span>

        </button>

      </div>

      <p class="hint">Enter — отправить&nbsp;&nbsp;·&nbsp;&nbsp;Shift+Enter — перенос строки</p>

    </footer>

  </div>

</template>


<script setup>

import { ref, nextTick } from 'vue'


const messages  = ref([])   // { id, role, content }

const draft     = ref('')

const loading   = ref(false)

const error     = ref('')

const messagesEl = ref(null)

const inputEl   = ref(null)

let   idSeq     = 0


// Максимальная длина сообщения пользователя

const MAX_LEN = 8000


function renderText(text) {

  // Безопасный рендер: экранируем HTML, затем оборачиваем параграфы и коды

  const esc = text

    .replace(/&/g, '&amp;')

    .replace(/</g, '&lt;')

    .replace(/>/g, '&gt;')

    .replace(/"/g, '&quot;')


  // Простой markdown: **bold**, *italic*, `code`, тройные ``` как блок кода

  return esc

    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')

    .replace(/`([^`]+)`/g, '<code>$1</code>')

    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

    .replace(/\*([^*]+)\*/g, '<em>$1</em>')

    .replace(/\n/g, '<br>')

}


async function scrollToBottom() {

  await nextTick()

  if (messagesEl.value) {

    messagesEl.value.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })

  }

}


function autoResize() {

  const el = inputEl.value

  if (!el) return

  el.style.height = 'auto'

  el.style.height = Math.min(el.scrollHeight, 200) + 'px'

}


function newline() {

  draft.value += '\n'

  nextTick(autoResize)

}


async function send() {

  const text = draft.value.trim()

  if (!text || loading.value) return


  if (text.length > MAX_LEN) {

    error.value = `Сообщение слишком длинное (максимум ${MAX_LEN} символов).`

    return

  }


  error.value = ''

  messages.value.push({ id: ++idSeq, role: 'user', content: text })

  draft.value = ''

  if (inputEl.value) { inputEl.value.style.height = 'auto' }

  await scrollToBottom()


  loading.value = true


  // Формируем историю для бэкенда

  const history = messages.value.map(m => ({ role: m.role, content: m.content }))


  try {

    const res = await fetch('/api/chat', {

      method: 'POST',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify({ messages: history }),

    })


    if (res.status === 429) {

      error.value = 'Слишком много запросов. Подождите немного.'

      return

    }


    if (!res.ok) {

      const data = await res.json().catch(() => ({}))

      error.value = data.detail || `Ошибка сервера (${res.status}).`

      return

    }


    const data = await res.json()

    messages.value.push({ id: ++idSeq, role: 'assistant', content: data.reply })

    await scrollToBottom()

  } catch (e) {

    error.value = 'Не удалось связаться с сервером. Проверьте, что бэкенд запущен.'

  } finally {

    loading.value = false

    await nextTick()

    inputEl.value?.focus()

  }

}


function clearChat() {

  messages.value = []

  error.value = ''

}

</script>


<style scoped>

/* ── Layout ──────────────────────────────────────────── */

.layout {

  display: flex;

  flex-direction: column;

  height: 100dvh;

  max-width: 720px;

  margin: 0 auto;

}


/* ── Header ─────────────────────────────────────────── */

.header {

  display: flex;

  align-items: center;

  justify-content: space-between;

  padding: 22px 28px 18px;

  border-bottom: 1px solid var(--border);

  flex-shrink: 0;

}

.logo {

  font-family: var(--font-serif);

  font-size: 22px;

  font-style: italic;

  color: var(--accent);

  letter-spacing: 0.02em;

}

.clear-btn {

  background: none;

  border: 1px solid transparent;

  color: var(--muted);

  cursor: pointer;

  padding: 6px 8px;

  border-radius: 8px;

  display: flex;

  align-items: center;

  transition: color .2s, border-color .2s;

}

.clear-btn:hover:not(:disabled) { color: var(--text); border-color: var(--border); }

.clear-btn:disabled { opacity: .3; cursor: default; }


/* ── Messages ───────────────────────────────────────── */

.messages {

  flex: 1;

  overflow-y: auto;

  padding: 32px 28px;

  display: flex;

  flex-direction: column;

}

.messages-inner { display: flex; flex-direction: column; gap: 28px; }


.empty {

  flex: 1;

  display: flex;

  flex-direction: column;

  align-items: center;

  justify-content: center;

  gap: 8px;

  text-align: center;

}

.empty-title {

  font-family: var(--font-serif);

  font-style: italic;

  font-size: 26px;

  color: var(--accent);

}

.empty-sub { color: var(--muted); font-size: 14px; }


.bubble-wrap { display: flex; flex-direction: column; gap: 5px; max-width: 88%; }

.bubble-wrap.user { align-self: flex-end; align-items: flex-end; }

.bubble-wrap.assistant { align-self: flex-start; align-items: flex-start; }


.label {

  font-size: 11px;

  font-weight: 500;

  letter-spacing: .08em;

  text-transform: uppercase;

  color: var(--muted);

  padding: 0 4px;

}


.bubble {

  padding: 14px 18px;

  border-radius: var(--radius);

  font-size: 15px;

  line-height: 1.7;

  word-break: break-word;

}

.bubble-wrap.user .bubble {

  background: var(--user-bg);

  border: 1px solid var(--border);

  border-bottom-right-radius: 4px;

}

.bubble-wrap.assistant .bubble {

  background: var(--ai-bg);

  border: 1px solid var(--border);

  border-bottom-left-radius: 4px;

}


/* code inside bubble */

.bubble :deep(pre) {

  background: #0a0a0b;

  border: 1px solid var(--border);

  border-radius: 8px;

  padding: 12px 14px;

  margin: 10px 0;

  overflow-x: auto;

  font-size: 13px;

}

.bubble :deep(code) {

  font-family: 'Fira Code', 'Cascadia Code', monospace;

  font-size: 13px;

  background: rgba(255,255,255,.06);

  padding: 1px 5px;

  border-radius: 4px;

}

.bubble :deep(pre code) { background: none; padding: 0; }


/* Typing dots */

.typing {

  display: flex;

  align-items: center;

  gap: 5px;

  padding: 16px 20px;

}

.typing span {

  width: 6px; height: 6px;

  border-radius: 50%;

  background: var(--accent-dim);

  animation: bounce 1.2s infinite;

}

.typing span:nth-child(2) { animation-delay: .2s; }

.typing span:nth-child(3) { animation-delay: .4s; }

@keyframes bounce {

  0%, 80%, 100% { transform: translateY(0); opacity: .4; }

  40%           { transform: translateY(-5px); opacity: 1; }

}


.error-msg {

  align-self: center;

  margin-top: 12px;

  display: flex;

  align-items: center;

  gap: 6px;

  color: #c97b7b;

  font-size: 13px;

  background: rgba(200, 80, 80, .08);

  border: 1px solid rgba(200,80,80,.2);

  padding: 8px 14px;

  border-radius: 8px;

}


/* ── Input area ─────────────────────────────────────── */

.input-area {

  padding: 16px 28px 20px;

  border-top: 1px solid var(--border);

  flex-shrink: 0;

}

.input-wrap {

  display: flex;

  align-items: flex-end;

  gap: 10px;

  background: var(--surface);

  border: 1px solid var(--border);

  border-radius: var(--radius);

  padding: 10px 10px 10px 18px;

  transition: border-color .2s;

}

.input-wrap:focus-within { border-color: var(--accent-dim); }


textarea {

  flex: 1;

  background: none;

  border: none;

  outline: none;

  resize: none;

  color: var(--text);

  font-family: var(--font-sans);

  font-size: 15px;

  line-height: 1.6;

  max-height: 200px;

  overflow-y: auto;

}

textarea::placeholder { color: var(--muted); }


.send-btn {

  background: var(--accent);

  color: #0e0e0f;

  border: none;

  border-radius: 9px;

  width: 38px; height: 38px;

  flex-shrink: 0;

  display: flex;

  align-items: center;

  justify-content: center;

  cursor: pointer;

  transition: opacity .2s, transform .15s;

}

.send-btn:hover:not(:disabled) { opacity: .85; transform: translateY(-1px); }

.send-btn:disabled { opacity: .3; cursor: default; transform: none; }


.spin {

  width: 16px; height: 16px;

  border: 2px solid rgba(0,0,0,.3);

  border-top-color: #0e0e0f;

  border-radius: 50%;

  animation: spin .6s linear infinite;

  display: block;

}

@keyframes spin { to { transform: rotate(360deg); } }


.hint { font-size: 11px; color: var(--muted); margin-top: 8px; text-align: center; letter-spacing: .02em; }


/* ── Transitions ────────────────────────────────────── */

.msg-enter-active { transition: opacity .25s ease, transform .25s ease; }

.msg-enter-from   { opacity: 0; transform: translateY(8px); }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }

.fade-enter-from, .fade-leave-to        { opacity: 0; }


/* ── Mobile ─────────────────────────────────────────── */

@media (max-width: 600px) {

  .header, .messages, .input-area { padding-left: 16px; padding-right: 16px; }

  .bubble-wrap { max-width: 96%; }

}

</style>
