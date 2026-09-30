"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useSession } from "@/components/session-provider";
import { WorkspaceShell } from "@/components/workspace-shell";
import { createConversation, listMessages, streamNiaReply, type NiaMessage } from "@/lib/eunia-api";
import styles from "./page.module.css";

const suggestions = ["Summarise this week's priorities", "Prepare a customer briefing", "Find the latest brand guidelines"];
const conversationKey = "eunia.activeConversation";

export default function DashboardPage() {
  const { session } = useSession();
  const firstName = session?.user.full_name.split(" ")[0] ?? "there";
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<NiaMessage[]>([]);
  const [conversationId, setConversationId] = useState("");
  const [error, setError] = useState("");
  const [thinking, setThinking] = useState(false);
  const messagePane = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!session) return;
    const savedId = sessionStorage.getItem(conversationKey);
    if (!savedId) return;

    setConversationId(savedId);
    listMessages(session.token, session.workspace.id, savedId)
      .then(setMessages)
      .catch(() => sessionStorage.removeItem(conversationKey));
  }, [session]);

  useEffect(() => {
    messagePane.current?.scrollTo({ top: messagePane.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  async function send(event: FormEvent) {
    event.preventDefault();
    await submitNiaPrompt(prompt);
  }

  async function submitNiaPrompt(rawPrompt: string) {
    if (!session || !rawPrompt.trim() || thinking) return;

    const content = rawPrompt.trim();
    setPrompt("");
    setThinking(true);
    setError("");
    let activeConversationId = conversationId;
    const localUser: NiaMessage = {
      id: `user-${Date.now()}`,
      conversation_id: activeConversationId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    try {
      if (!activeConversationId) {
        const conversation = await createConversation(session.token, session.workspace.id);
        activeConversationId = conversation.id;
        setConversationId(activeConversationId);
        sessionStorage.setItem(conversationKey, activeConversationId);
        localUser.conversation_id = activeConversationId;
      }

      const assistantId = `assistant-${Date.now()}`;
      const localAssistant: NiaMessage = {
        id: assistantId,
        conversation_id: activeConversationId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
      };
      setMessages((items) => [...items, localUser, localAssistant]);

      await streamNiaReply(session.token, session.workspace.id, activeConversationId, content, (delta) => {
        setMessages((items) => items.map((message) => (
          message.id === assistantId ? { ...message, content: message.content + delta } : message
        )));
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "NIA could not respond.");
    } finally {
      setThinking(false);
    }
  }

  return (
    <WorkspaceShell>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>YOUR AI WORKSPACE</p>
          <h1>Good morning, {firstName} <span>{"\u2726"}</span></h1>
          <p>Here&apos;s what&apos;s happening across your AI workspace today.</p>
        </div>
        <button className={styles.inviteButton} type="button"><span>+</span> Invite team</button>
      </section>

      <section className={styles.askCard}>
        <div className={styles.askHeader}>
          <Image className={styles.euniaMark} src="/brand/eunia-nia-mark.png" alt="" width={34} height={34} priority />
          <div>
            <strong>Ask NIA</strong>
            <span>Your secure AI workspace</span>
          </div>
          <span className={styles.secure}>{"\u25cf"} Private &amp; secure</span>
        </div>

        <div className={styles.messagePane} ref={messagePane} aria-live="polite">
          {messages.length === 0 && (
            <div className={styles.emptyChat}>
              <span>{"\u2726"}</span>
              <p>Ask NIA anything to begin a focused conversation.</p>
            </div>
          )}
          {messages.map((message) => (
            <article className={message.role === "assistant" ? styles.assistantMessage : styles.userMessage} key={message.id}>
              <strong>{message.role === "assistant" ? "NIA" : "You"}</strong>
              <p>{message.content || "NIA is thinking..."}</p>
            </article>
          ))}
          {error && <p className={styles.error}>{error}</p>}
        </div>

        <form className={styles.composer} onSubmit={send}>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            aria-label="Ask NIA"
            placeholder="Message NIA..."
            rows={2}
          />
          <div className={styles.askFooter}>
            <div className={styles.suggestions}>
              {suggestions.map((suggestion) => (
                <button type="button" onClick={() => setPrompt(suggestion)} key={suggestion}>{suggestion}</button>
              ))}
            </div>
            <div className={styles.composerActions}>
              <button className={styles.sendButton} aria-label="Send request" disabled={thinking} type="submit">
                {thinking ? "..." : "\u2191"}
              </button>
            </div>
          </div>
        </form>
      </section>

      <section className={styles.metrics}>
        <article><span className={styles.metricIcon}>{"\u2726"}</span><div><strong>8</strong><span>Active AI employees</span></div><small className={styles.positive}>{"\u2191"} 2 this month</small></article>
        <article><span className={`${styles.metricIcon} ${styles.blue}`}>{"\u2197"}</span><div><strong>1,284</strong><span>Tasks completed</span></div><small className={styles.positive}>{"\u2191"} 18% vs. last month</small></article>
        <article><span className={`${styles.metricIcon} ${styles.orange}`}>{"\u25f7"}</span><div><strong>42.6h</strong><span>Time saved</span></div><small className={styles.positive}>{"\u2191"} 6.4h this week</small></article>
      </section>
    </WorkspaceShell>
  );
}
