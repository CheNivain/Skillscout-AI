import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import {
  ArrowRight,
  Bell,
  Check,
  Clock3,
  LoaderCircle,
  Send,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api, date } from './api';
import { Drawer, Empty, Spinner } from './components';
import type { ChatResponse, Course, Notification } from './types';
import { useWorkspace } from './workspace';

type Message = { role: 'user' | 'assistant'; text: string; sources?: Course[]; llm?: boolean };
export function ChatPanel({ onClose }: { onClose: () => void }) {
  const { dashboard, selectCourse, go } = useWorkspace();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);
  async function ask(text: string) {
    if (busy || !text.trim()) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: text.trim() }]);
    setBusy(true);
    setError('');
    try {
      const answer = await api<ChatResponse>('/chat', 'POST', { message: text.trim() });
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: answer.answer, sources: answer.sources, llm: answer.llm_used },
      ]);
    } catch (e) {
      setError((e as Error).message);
      setInput(text);
    } finally {
      setBusy(false);
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(input);
  }
  return (
    <Drawer title="Ask Scout" subtitle="YOUR LEARNING ASSISTANT" onClose={onClose}>
      <div className="chat-disclosure">
        <ShieldCheck size={15} />
        <span>
          Answers use retrieved catalogue sources. Check provider details before enrolling. Each
          question is processed independently.
        </span>
      </div>
      {!dashboard.profile.consent ? (
        <Empty
          icon={<ShieldCheck size={28} />}
          title="Analysis consent required"
          text="Enable personalized learning analysis in your profile to ask Scout about your goals and course opportunities."
          action={
            <button
              className="button primary"
              onClick={() => {
                onClose();
                go('settings');
              }}
            >
              Open privacy preferences <ArrowRight size={15} />
            </button>
          }
        />
      ) : (
        <>
          <div className="chat-messages">
            {!messages.length && (
              <div className="chat-welcome">
                <span className="scout-symbol">
                  <Sparkles size={30} />
                </span>
                <h3>How can I help?</h3>
                <p>Ask about courses, skills or your career goal.</p>
                <div className="chat-suggestions">
                  {[
                    'What should I learn next?',
                    'Find an affordable Python course',
                    'Which certifications match my career goal?',
                  ].map((s) => (
                    <button key={s} onClick={() => void ask(s)}>
                      {s}
                      <ArrowRight size={14} />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message, index) => (
              <article key={index} className={`chat-message ${message.role}`}>
                <div className="message-role">
                  {message.role === 'assistant' && <Sparkles size={14} />}
                  <strong>{message.role === 'user' ? 'You' : 'Scout'}</strong>
                  {message.role === 'assistant' && (
                    <span>{message.llm ? 'Local Ollama' : 'Grounded rules-based response'}</span>
                  )}
                </div>
                <p>{message.text}</p>
                {message.sources && message.sources.length > 0 && (
                  <div className="chat-sources">
                    <small>CATALOGUE SOURCES</small>
                    {message.sources.map((course, i) => (
                      <button
                        key={course.id}
                        onClick={() => {
                          onClose();
                          selectCourse(course);
                        }}
                      >
                        <span>{i + 1}</span>
                        <div>
                          <strong>{course.title}</strong>
                          <small>{course.provider}</small>
                        </div>
                        <ArrowRight size={14} />
                      </button>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {busy && (
              <div className="chat-thinking" role="status">
                <LoaderCircle size={17} className="spin" />
                Finding a grounded answer…
              </div>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <div ref={end} />
          </div>
          <form onSubmit={submit} className="chat-composer">
            <textarea
              aria-label="Ask Scout"
              rows={2}
              maxLength={800}
              placeholder="Ask about a skill, course, or your next move…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void ask(input);
                }
              }}
            />
            <button
              className="button primary"
              aria-label="Send message"
              disabled={busy || !input.trim()}
            >
              <Send size={18} />
            </button>
            <small>{input.length}/800 · Conversations are not stored</small>
          </form>
        </>
      )}
    </Drawer>
  );
}

export function NotificationsPanel({ onClose }: { onClose: () => void }) {
  const { refresh, selectCourse, toast } = useWorkspace();
  const [notes, setNotes] = useState<Notification[] | null>(null);
  const [error, setError] = useState('');
  const [marking, setMarking] = useState(false);
  async function load() {
    try {
      setNotes(await api<Notification[]>('/notifications'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function read(note: Notification) {
    try {
      if (!note.read) {
        await api(`/notifications/${encodeURIComponent(note.id)}/read`, 'POST');
        setNotes((rows) => rows?.map((n) => (n.id === note.id ? { ...n, read: true } : n)) || null);
        await refresh();
      }
    } catch (e) {
      toast((e as Error).message, true);
    }
  }
  async function open(note: Notification) {
    await read(note);
    if (note.course_id) {
      try {
        const course = await api<Course>(`/courses/${encodeURIComponent(note.course_id)}`);
        onClose();
        selectCourse(course);
      } catch (e) {
        toast((e as Error).message, true);
      }
    }
  }
  async function markAll() {
    setMarking(true);
    try {
      await api('/notifications/all/read', 'POST');
      await load();
      await refresh();
    } catch (e) {
      toast((e as Error).message, true);
    } finally {
      setMarking(false);
    }
  }
  return (
    <Drawer title="Notifications" subtitle="OPPORTUNITY NOTIFICATIONS" onClose={onClose}>
      <div className="drawer-content">
        {notes && notes.some((n) => !n.read) && (
          <div className="notification-toolbar">
            <span>{notes.filter((n) => !n.read).length} unread opportunities</span>
            <button className="text-button" disabled={marking} onClick={() => void markAll()}>
              <Check size={15} />
              Mark all read
            </button>
          </div>
        )}
        {error ? (
          <Empty
            title="Couldn’t load your notifications."
            text={error}
            action={
              <button className="button secondary" onClick={() => void load()}>
                Try again
              </button>
            }
          />
        ) : notes === null ? (
          <Spinner />
        ) : notes.length ? (
          <div className="notifications-list">
            {notes.map((note) => (
              <article
                className={`notification-item ${note.read ? 'read' : 'unread'}`}
                key={note.id}
              >
                <div className="notification-icon">
                  <Bell size={18} />
                </div>
                <div>
                  <div className="notification-title">
                    <h3>{note.title}</h3>
                    {!note.read && <span className="status-dot" />}
                  </div>
                  <p>{note.message}</p>
                  <small>
                    <Clock3 size={12} />
                    {date(note.created_at)} ·{' '}
                    {new Date(note.created_at).toLocaleTimeString(undefined, {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </small>
                  <div className="notification-actions">
                    {note.course_id && (
                      <button className="text-button" onClick={() => void open(note)}>
                        View opportunity <ArrowRight size={14} />
                      </button>
                    )}
                    {!note.read && (
                      <button className="text-button muted" onClick={() => void read(note)}>
                        Mark read
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty
            icon={<Bell size={28} />}
            title="A quiet inbox, for now."
            text="Enable opportunity notifications in your profile. The agents will let you know when a recommendation meets the priority threshold."
          />
        )}
      </div>
    </Drawer>
  );
}
