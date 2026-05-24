import { Bot, MessageCircle, UserRound } from "lucide-react";
import type { ConversationTurn } from "@/lib/api/types";
import { formatDateTime, statusLabel } from "@/lib/state/format";

type ConversationPanelProps = {
  turns: ConversationTurn[];
};

export function ConversationPanel({ turns }: ConversationPanelProps) {
  const recentTurns = turns.slice(-8);

  return (
    <section className="conversation-panel" aria-label="Conversation history">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dialogue</p>
          <h2>Back-and-forth run history</h2>
        </div>
        <span>{turns.length} turns</span>
      </div>

      {recentTurns.length === 0 ? (
        <div className="empty-state compact">
          <MessageCircle size={22} aria-hidden="true" />
          <p>Your conversation with the content agents will appear here.</p>
        </div>
      ) : (
        <div className="turn-list">
          {recentTurns.map((turn) => {
            const fromUser = turn.speaker === "user";
            return (
              <article className={fromUser ? "turn user-turn" : "turn assistant-turn"} key={turn.turn_id}>
                <div className="turn-icon" aria-hidden="true">
                  {fromUser ? <UserRound size={16} /> : <Bot size={16} />}
                </div>
                <div>
                  <div className="turn-meta">
                    <span>{statusLabel(turn.speaker)}</span>
                    <span>{statusLabel(turn.modality)}</span>
                    <span>{formatDateTime(turn.created_at)}</span>
                  </div>
                  <p>{turn.transcript}</p>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
