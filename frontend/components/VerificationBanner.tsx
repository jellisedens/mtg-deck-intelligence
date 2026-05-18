"use client";

import { useState } from "react";
import { isVerified, getToken } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function VerificationBanner() {
  const [dismissed, setDismissed] = useState(false);
  const [resending, setResending] = useState(false);
  const [sent, setSent] = useState(false);
  const verified = isVerified();

  if (verified || dismissed) return null;

  const handleResend = async () => {
    setResending(true);
    try {
      const t = getToken();
      await fetch(`${API_BASE}/auth/resend-verification`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${t}`,
        },
      });
      setSent(true);
    } catch {
      // ignore
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="bg-amber-900/30 border border-amber-700/50 rounded-lg px-4 py-3 mb-4 flex items-center justify-between">
      <div className="text-sm text-amber-200">
        {sent ? (
          "Verification email sent — check your inbox (and spam folder)."
        ) : (
          <>
            Verify your email to unlock AI suggestions, strategy generation, and simulation.{" "}
            <button
              onClick={handleResend}
              disabled={resending}
              className="underline hover:text-amber-100 disabled:opacity-50"
            >
              {resending ? "Sending..." : "Resend verification email"}
            </button>
          </>
        )}
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-amber-400 hover:text-amber-200 ml-4 text-lg"
      >
        ✕
      </button>
    </div>
  );
}