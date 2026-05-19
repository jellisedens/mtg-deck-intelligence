"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

function VerifyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided.");
      return;
    }

    fetch(`${API_BASE}/auth/verify?token=${token}`)
      .then(async (res) => {
        const data = await res.json();
        if (res.ok) {
          setStatus("success");
          setMessage(data.message || "Email verified successfully!");
          if (typeof window !== "undefined") {
            localStorage.setItem("mtg_verified", "true");
          }
        } else {
          setStatus("error");
          setMessage(data.detail || "Verification failed.");
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage("Network error. Please try again.");
      });
  }, [searchParams]);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 max-w-md w-full text-center">
      {status === "loading" && (
        <>
          <div className="animate-spin h-8 w-8 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-400">Verifying your email...</p>
        </>
      )}

      {status === "success" && (
        <>
          <div className="text-4xl mb-4">✓</div>
          <h1 className="text-xl font-bold text-white mb-2">Verified!</h1>
          <p className="text-gray-400 mb-6">{message}</p>
          <button
            onClick={() => router.push("/decks")}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg"
          >
            Go to My Decks
          </button>
        </>
      )}

      {status === "error" && (
        <>
          <div className="text-4xl mb-4">✗</div>
          <h1 className="text-xl font-bold text-white mb-2">Verification Failed</h1>
          <p className="text-gray-400 mb-6">{message}</p>
          <button
            onClick={() => router.push("/auth/login")}
            className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded-lg"
          >
            Go to Login
          </button>
        </>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <Suspense fallback={
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 max-w-md w-full text-center">
          <div className="animate-spin h-8 w-8 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-400">Loading...</p>
        </div>
      }>
        <VerifyContent />
      </Suspense>
    </div>
  );
}