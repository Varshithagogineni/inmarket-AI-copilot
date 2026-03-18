import { useEffect, useRef, useState } from "react";
import { ChatMessage, MessageType } from "./components/ChatMessage";
import { ChatInput } from "./components/ChatInput";
import { Sidebar } from "./components/Sidebar";
import {
  createCampaignRun,
  getCampaignRun,
  listCampaignRuns,
  refineCampaignRun,
} from "./features/copilot/api";
import type {
  CampaignRunResponse,
  RefineRunRequest,
  RunSummary,
} from "./types";

export function App() {
  const [messages, setMessages] = useState<MessageType[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hey! I'm your Event Surge Activation Copilot. Tell me about a campaign you want to run — like the city, timing, audience, and brand category — and I'll find the best local event, build a brief, generate copy, and create a draft poster.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeRun, setActiveRun] = useState<CampaignRunResponse | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void listCampaignRuns().then(setRuns);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (msg: Omit<MessageType, "id" | "timestamp">) => {
    const newMsg: MessageType = {
      ...msg,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newMsg]);
    return newMsg;
  };

  const handleSend = async (text: string) => {
    addMessage({ role: "user", content: text });

    // Check if this is a refinement request on an active run
    const isRefine = activeRun && isRefinementRequest(text);

    setIsLoading(true);
    addMessage({ role: "assistant", content: "thinking", isThinking: true });

    try {
      let result: CampaignRunResponse;

      if (isRefine && activeRun) {
        const refineReq = parseRefinement(text);
        result = await refineCampaignRun(activeRun.run_id, refineReq);
        setMessages((prev) => prev.filter((m) => !m.isThinking));
        addMessage({
          role: "assistant",
          content: `Refined the ${refineReq.target}. Here's the updated output:`,
          runData: result,
          showSection: refineReq.target,
        });
      } else {
        result = await createCampaignRun({ prompt: text });
        setMessages((prev) => prev.filter((m) => !m.isThinking));
        addMessage({
          role: "assistant",
          content: buildSummaryMessage(result),
          runData: result,
        });
      }

      setActiveRun(result);
      const updatedRuns = await listCampaignRuns();
      setRuns(updatedRuns);
    } catch {
      setMessages((prev) => prev.filter((m) => !m.isThinking));
      addMessage({
        role: "assistant",
        content: "Something went wrong. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectRun = async (runId: string) => {
    const result = await getCampaignRun(runId);
    setActiveRun(result);
    addMessage({
      role: "assistant",
      content: `Loaded previous run for **${result.selected_event.name}**:`,
      runData: result,
    });
  };

  return (
    <div className="chat-app">
      <Sidebar
        runs={runs}
        activeRunId={activeRun?.run_id}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onSelect={handleSelectRun}
        onNewChat={() => {
          setActiveRun(null);
          setMessages([
            {
              id: "welcome",
              role: "assistant",
              content: "Starting fresh! What campaign would you like to build?",
              timestamp: new Date().toISOString(),
            },
          ]);
        }}
      />
      <main className={`chat-main ${sidebarOpen ? "" : "chat-main-full"}`}>
        <header className="chat-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            type="button"
          >
            {sidebarOpen ? "\u2190" : "\u2630"}
          </button>
          <div>
            <h1>Event Surge Copilot</h1>
            <span className="chat-subtitle">AI-powered activation planning</span>
          </div>
        </header>
        <div className="chat-messages">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </main>
    </div>
  );
}

function isRefinementRequest(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("refine") ||
    lower.includes("change the") ||
    lower.includes("make it") ||
    lower.includes("update the") ||
    lower.includes("more ") ||
    lower.includes("less ") ||
    lower.includes("try a different") ||
    lower.includes("regenerate")
  );
}

function parseRefinement(text: string): RefineRunRequest {
  const lower = text.toLowerCase();
  let target: RefineRunRequest["target"] = "copy";
  if (lower.includes("image") || lower.includes("poster") || lower.includes("visual") || lower.includes("photo")) {
    target = "image";
  } else if (lower.includes("brief") || lower.includes("strategy") || lower.includes("angle")) {
    target = "brief";
  }
  return { instruction: text, target };
}

function buildSummaryMessage(result: CampaignRunResponse): string {
  const recs = result.recommendations ?? [];
  if (recs.length >= 2) {
    return `Found **${recs.length} top events** for you! Here are full campaign recommendations for each — with briefs, copy, and generated posters:`;
  }
  const ev = result.selected_event;
  return `Found **${ev.name}** at ${ev.venue_name || ev.city} (score: ${ev.score}/100). I've generated a campaign brief, copy assets, and a creative direction:`;
}
