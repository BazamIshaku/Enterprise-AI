"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import type { KokoroTTS } from "kokoro-js";
import { useSession } from "@/components/session-provider";
import { WorkspaceShell } from "@/components/workspace-shell";
import { createConversation, listMessages, streamNiaReply, type NiaMessage } from "@/lib/eunia-api";
import styles from "./page.module.css";

const suggestions = ["Summarise this week's priorities", "Prepare a customer briefing", "Find the latest brand guidelines"];
const conversationKey = "eunia.activeConversation";
const kokoroModel = "onnx-community/Kokoro-82M-v1.0-ONNX";

let niaVoicePromise: Promise<KokoroTTS> | null = null;
let activeNiaAudio: { audio: HTMLAudioElement; finish: () => void } | null = null;
let niaSpeechSession = 0;

type SpeechResult = {
  0: { transcript: string };
  isFinal: boolean;
};

type SpeechResultEvent = Event & {
  results: { [index: number]: SpeechResult; length: number };
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: Event & { error: string }) => void) | null;
  onresult: ((event: SpeechResultEvent) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type BrowserSpeechWindow = Window & typeof globalThis & {
  SpeechRecognition?: new () => BrowserSpeechRecognition;
  webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
};

function loadNiaVoice(): Promise<KokoroTTS> {
  if (!niaVoicePromise) {
    niaVoicePromise = import("kokoro-js")
      .then(({ KokoroTTS }) => KokoroTTS.from_pretrained(kokoroModel, { dtype: "q8", device: "wasm" }))
      .catch((error) => {
        niaVoicePromise = null;
        throw error;
      });
  }

  return niaVoicePromise;
}

function stopNiaVoice() {
  niaSpeechSession += 1;
  if (!activeNiaAudio) return;

  const activeAudio = activeNiaAudio;
  activeNiaAudio = null;
  activeAudio.audio.pause();
  activeAudio.finish();
}

function speechText(markdown: string) {
  return markdown
    .replace(/```[\s\S]*?```/g, " I have included the code in the chat. ")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[\*_~`|]+/g, "")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*(?:[-+]\s+|\d+[.)]\s+)/gm, "")
    .replace(/^\s*>\s?/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

function takeSpeechChunk(buffer: string, flush = false) {
  const boundary = /[.!?](?=\s|$)/g;
  let lastBoundary = -1;
  let match: RegExpExecArray | null;

  while ((match = boundary.exec(buffer)) !== null) lastBoundary = match.index + 1;
  if (lastBoundary > 0) return [buffer.slice(0, lastBoundary), buffer.slice(lastBoundary)];
  if (flush) return [buffer, ""];
  if (buffer.length < 140) return ["", buffer];

  const cutAt = buffer.lastIndexOf(" ", 118);
  return [buffer.slice(0, cutAt > 0 ? cutAt : 118), buffer.slice(cutAt > 0 ? cutAt : 118)];
}

async function speakNiaChunk(text: string, session: number, onStatus: (status: "speaking" | "ready") => void) {
  const spokenText = speechText(text);
  if (!spokenText || session !== niaSpeechSession) return;

  const voice = await loadNiaVoice();
  if (session !== niaSpeechSession) return;

  const generatedAudio = await voice.generate(spokenText, { voice: "af_heart", speed: 1.12 });
  if (session !== niaSpeechSession) return;

  const audioUrl = URL.createObjectURL(generatedAudio.toBlob());
  const audio = new Audio(audioUrl);

  await new Promise<void>((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      audio.onended = null;
      audio.onerror = null;
      if (activeNiaAudio?.audio === audio) activeNiaAudio = null;
      URL.revokeObjectURL(audioUrl);
      resolve();
    };

    activeNiaAudio = { audio, finish };
    audio.onended = finish;
    audio.onerror = finish;
    onStatus("speaking");
    void audio.play().catch(finish);
  });

  if (session === niaSpeechSession) onStatus("ready");
}

export default function DashboardPage() {
  const { session } = useSession();
  const firstName = session?.user.full_name.split(" ")[0] ?? "there";
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<NiaMessage[]>([]);
  const [conversationId, setConversationId] = useState("");
  const [error, setError] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [voiceInputError, setVoiceInputError] = useState("");
  const [thinking, setThinking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<"off" | "loading" | "ready" | "speaking">("off");
  const [voiceTapping, setVoiceTapping] = useState(false);
  const [listening, setListening] = useState(false);
  const messagePane = useRef<HTMLDivElement>(null);
  const voiceRequested = useRef(false);
  const recognition = useRef<BrowserSpeechRecognition | null>(null);
  const transcript = useRef("");
  const promptBeforeListening = useRef("");
  const submitTranscript = useRef(false);
  const voiceInputFailed = useRef(false);
  const voiceInputStopping = useRef(false);

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

  useEffect(() => () => {
    recognition.current?.abort();
    stopNiaVoice();
  }, []);

  async function enableNiaVoice() {
    voiceRequested.current = true;
    setVoiceEnabled(true);
    setVoiceStatus("loading");
    setVoiceError("");

    try {
      await loadNiaVoice();
      if (voiceRequested.current) setVoiceStatus("ready");
    } catch {
      voiceRequested.current = false;
      setVoiceEnabled(false);
      setVoiceStatus("off");
      setVoiceError("NIA's voice could not load. Check your internet connection and try again.");
    }
  }

  function toggleVoice() {
    setVoiceTapping(true);
    window.setTimeout(() => setVoiceTapping(false), 420);

    if (recognition.current) {
      submitTranscript.current = false;
      recognition.current.abort();
    }

    if (voiceEnabled) {
      voiceRequested.current = false;
      stopNiaVoice();
      setVoiceEnabled(false);
      setVoiceStatus("off");
      setVoiceError("");
      return;
    }

    void enableNiaVoice();
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    await submitNiaPrompt(prompt);
  }

  function startVoiceInput() {
    if (thinking || recognition.current) return;

    const browserWindow = window as BrowserSpeechWindow;
    const SpeechRecognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceInputError("Voice input is available in the latest Chrome or Edge. Please use one of those browsers and allow microphone access.");
      return;
    }

    if (voiceRequested.current) {
      stopNiaVoice();
      setVoiceStatus("ready");
    }

    const nextRecognition = new SpeechRecognition();
    recognition.current = nextRecognition;
    transcript.current = "";
    promptBeforeListening.current = prompt;
    submitTranscript.current = false;
    voiceInputFailed.current = false;
    voiceInputStopping.current = false;
    setVoiceInputError("");
    setPrompt("");
    nextRecognition.continuous = false;
    nextRecognition.interimResults = true;
    nextRecognition.lang = "en-US";

    nextRecognition.onresult = (event) => {
      const nextTranscript = Array.from({ length: event.results.length }, (_, index) => event.results[index][0].transcript)
        .join("")
        .trim();
      transcript.current = nextTranscript;
      setPrompt(nextTranscript);
    };

    nextRecognition.onerror = (event) => {
      if (event.error === "aborted") return;
      voiceInputFailed.current = true;
      const message = event.error === "not-allowed" || event.error === "service-not-allowed"
        ? "Microphone access is blocked. Allow it in your browser, then try Talk again."
        : event.error === "no-speech"
          ? "NIA did not hear anything. Hold Talk while you speak, then release it."
          : "NIA could not hear you clearly. Please try Talk again.";
      setVoiceInputError(message);
    };

    nextRecognition.onend = () => {
      const spokenPrompt = transcript.current.trim();
      const shouldSubmit = submitTranscript.current;
      recognition.current = null;
      submitTranscript.current = false;
      voiceInputStopping.current = false;
      setListening(false);

      if (shouldSubmit && spokenPrompt && !voiceInputFailed.current) {
        void submitNiaPrompt(spokenPrompt);
      } else if (!spokenPrompt) {
        setPrompt(promptBeforeListening.current);
      }
    };

    try {
      nextRecognition.start();
      setListening(true);
    } catch {
      recognition.current = null;
      voiceInputStopping.current = false;
      setPrompt(promptBeforeListening.current);
      setVoiceInputError("NIA could not start voice input. Please try Talk again.");
    }
  }

  function finishVoiceInput() {
    if (!recognition.current || voiceInputStopping.current) return;
    voiceInputStopping.current = true;
    submitTranscript.current = true;
    recognition.current.stop();
  }

  async function submitNiaPrompt(rawPrompt: string) {
    if (!session || !rawPrompt.trim() || thinking) return;

    const content = rawPrompt.trim();
    setPrompt("");
    setThinking(true);
    setError("");
    setVoiceError("");
    setVoiceInputError("");
    const speechSession = voiceRequested.current ? (() => {
      stopNiaVoice();
      setVoiceStatus("ready");
      return niaSpeechSession;
    })() : -1;
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

      let speechBuffer = "";
      let speechQueue = Promise.resolve();
      let speechFailed = false;

      const queueSpeech = (chunk: string) => {
        if (!chunk || speechFailed || speechSession !== niaSpeechSession || !voiceRequested.current) return;

        speechQueue = speechQueue
          .then(() => speakNiaChunk(chunk, speechSession, setVoiceStatus))
          .catch(() => {
            if (speechSession === niaSpeechSession) {
              speechFailed = true;
              setVoiceStatus("ready");
              setVoiceError("NIA generated a response, but the audio could not play. Try the Voice button again.");
            }
          });
      };

      const queueAvailableSpeech = (flush = false) => {
        while (speechBuffer) {
          const [chunk, remainder] = takeSpeechChunk(speechBuffer, flush);
          speechBuffer = remainder;
          if (!chunk) break;
          queueSpeech(chunk);
        }
      };

      await streamNiaReply(session.token, session.workspace.id, activeConversationId, content, (delta) => {
        speechBuffer += delta;
        queueAvailableSpeech();
        setMessages((items) => items.map((message) => (
          message.id === assistantId ? { ...message, content: message.content + delta } : message
        )));
      });
      queueAvailableSpeech(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "NIA could not respond.");
    } finally {
      setThinking(false);
    }
  }

  const voiceDescription = listening
    ? "Listening... release Talk to send"
    : !voiceEnabled
      ? "Your secure AI workspace"
      : voiceStatus === "loading"
        ? "Preparing NIA's female AI voice..."
        : voiceStatus === "speaking"
          ? "NIA is speaking"
          : "Female AI voice ready";

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
            <span>{voiceDescription}</span>
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
          {voiceError && <p className={styles.error}>{voiceError}</p>}
          {voiceInputError && <p className={styles.error}>{voiceInputError}</p>}
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
              <button
                className={`${styles.voiceOrb} ${voiceEnabled ? styles.voiceOrbActive : ""} ${voiceTapping ? styles.voiceOrbTapping : ""}`}
                type="button"
                onClick={toggleVoice}
                aria-pressed={voiceEnabled}
                aria-label={voiceEnabled ? "Turn NIA voice off" : "Turn NIA voice on"}
                title={voiceEnabled ? "Turn NIA's spoken replies off" : "Turn NIA's spoken replies on"}
              >
                <span className={styles.voiceOrbRings} aria-hidden="true" />
                <span className={styles.voiceOrbSpeaker} aria-hidden="true" />
                <span className={styles.voiceOrbLabel}>{voiceEnabled ? "Voice on" : "Voice"}</span>
              </button>
              <div className={styles.submitActions}>
                <button
                  className={`${styles.talkButton} ${listening ? styles.talkButtonListening : ""}`}
                  type="button"
                  disabled={thinking}
                  onPointerDown={(event) => {
                    event.preventDefault();
                    event.currentTarget.setPointerCapture(event.pointerId);
                    startVoiceInput();
                  }}
                  onPointerUp={finishVoiceInput}
                  onPointerCancel={finishVoiceInput}
                  onLostPointerCapture={finishVoiceInput}
                  onKeyDown={(event) => {
                    if (!event.repeat && (event.key === " " || event.key === "Enter")) {
                      event.preventDefault();
                      startVoiceInput();
                    }
                  }}
                  onKeyUp={(event) => {
                    if (event.key === " " || event.key === "Enter") {
                      event.preventDefault();
                      finishVoiceInput();
                    }
                  }}
                  aria-label={listening ? "Listening. Release to send your message" : "Hold to talk to NIA"}
                  title={listening ? "Release to send" : "Hold to talk"}
                >
                  <span className={styles.talkMic} aria-hidden="true" />
                  <span>{listening ? "Listening" : "Talk"}</span>
                </button>
                <button className={styles.sendButton} aria-label="Send request" disabled={thinking} type="submit">
                  {thinking ? "..." : "\u2191"}
                </button>
              </div>
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
